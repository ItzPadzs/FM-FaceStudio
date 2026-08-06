using System.Text.Json;
using BepInEx;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;

namespace FMFaceStudioBridge;

[BepInPlugin(PluginGuid, PluginName, PluginVersion)]
public sealed class Plugin : BasePlugin
{
    public const string PluginGuid = "com.itzpadzs.fmfacestudio.bridge";
    public const string PluginName = "FM FaceStudio Bridge";
    public const string PluginVersion = "0.1.0";

    private readonly CancellationTokenSource _shutdown = new();
    private Task? _worker;
    private BridgePaths? _paths;

    public override void Load()
    {
        _paths = BridgePaths.Create();
        _paths.EnsureCreated();

        Log.LogInfo($"{PluginName} {PluginVersion} loading");
        Log.LogInfo($"Bridge directory: {_paths.Root}");

        WriteStatus("connected", null);
        _worker = Task.Run(() => RunBridgeLoopAsync(_shutdown.Token));
    }

    public override bool Unload()
    {
        _shutdown.Cancel();
        try
        {
            _worker?.Wait(TimeSpan.FromSeconds(2));
        }
        catch (AggregateException)
        {
            // Shutdown cancellation is expected.
        }

        WriteStatus("disconnected", null);
        _shutdown.Dispose();
        return true;
    }

    private async Task RunBridgeLoopAsync(CancellationToken cancellationToken)
    {
        if (_paths is null)
        {
            return;
        }

        while (!cancellationToken.IsCancellationRequested)
        {
            try
            {
                WriteStatus("connected", null);
                ProcessCommands(_paths, Log);
            }
            catch (Exception exception)
            {
                Log.LogWarning($"Bridge loop failed: {exception}");
                WriteStatus("error", exception.Message);
            }

            await Task.Delay(TimeSpan.FromSeconds(1), cancellationToken).ConfigureAwait(false);
        }
    }

    private static void ProcessCommands(BridgePaths paths, ManualLogSource log)
    {
        foreach (string commandPath in Directory.EnumerateFiles(paths.Commands, "*.json"))
        {
            string fileName = Path.GetFileName(commandPath);
            string processingPath = Path.Combine(paths.Processing, fileName);

            try
            {
                File.Move(commandPath, processingPath, overwrite: false);
                BridgeCommand? command = JsonSerializer.Deserialize<BridgeCommand>(
                    File.ReadAllText(processingPath), BridgeJson.Options);

                if (command is null || string.IsNullOrWhiteSpace(command.Type))
                {
                    throw new InvalidDataException("Command type is required.");
                }

                BridgeResponse response = command.Type.ToLowerInvariant() switch
                {
                    "ping" => BridgeResponse.Ok(command.Id, "pong"),
                    "publish-player" => PublishPlayer(paths, command),
                    _ => BridgeResponse.Fail(command.Id, $"Unsupported command: {command.Type}"),
                };

                string responseName = string.IsNullOrWhiteSpace(command.Id)
                    ? $"{Guid.NewGuid():N}.json"
                    : $"{command.Id}.json";
                AtomicJson.Write(Path.Combine(paths.Responses, responseName), response);
            }
            catch (Exception exception)
            {
                log.LogWarning($"Could not process command {fileName}: {exception.Message}");
                AtomicJson.Write(
                    Path.Combine(paths.Responses, $"failed-{Guid.NewGuid():N}.json"),
                    BridgeResponse.Fail(null, exception.Message));
            }
            finally
            {
                TryDelete(processingPath);
            }
        }
    }

    private static BridgeResponse PublishPlayer(BridgePaths paths, BridgeCommand command)
    {
        if (command.Player is null || command.Player.Id <= 0 || string.IsNullOrWhiteSpace(command.Player.Name))
        {
            return BridgeResponse.Fail(command.Id, "publish-player requires a positive player id and name.");
        }

        PlayerSelection selection = command.Player with
        {
            CapturedAtUtc = DateTimeOffset.UtcNow,
            Source = string.IsNullOrWhiteSpace(command.Player.Source) ? "bridge-command" : command.Player.Source,
        };
        AtomicJson.Write(paths.SelectedPlayer, selection);
        return BridgeResponse.Ok(command.Id, "player-published");
    }

    private void WriteStatus(string state, string? error)
    {
        if (_paths is null)
        {
            return;
        }

        AtomicJson.Write(_paths.Status, new BridgeStatus(
            PluginVersion,
            state,
            Environment.ProcessId,
            DateTimeOffset.UtcNow,
            error));
    }

    private static void TryDelete(string path)
    {
        try
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
        catch
        {
            // A stale processing file can be retried or removed manually.
        }
    }
}

internal sealed record BridgeStatus(
    string Version,
    string State,
    int ProcessId,
    DateTimeOffset UpdatedAtUtc,
    string? Error);

internal sealed record BridgeCommand(string? Id, string Type, PlayerSelection? Player);

internal sealed record PlayerSelection(
    long Id,
    string Name,
    string? Club,
    string? Nation,
    string? Source,
    DateTimeOffset? CapturedAtUtc);

internal sealed record BridgeResponse(string? Id, bool Success, string Message, DateTimeOffset RespondedAtUtc)
{
    public static BridgeResponse Ok(string? id, string message) =>
        new(id, true, message, DateTimeOffset.UtcNow);

    public static BridgeResponse Fail(string? id, string message) =>
        new(id, false, message, DateTimeOffset.UtcNow);
}

internal sealed record BridgePaths(
    string Root,
    string Commands,
    string Processing,
    string Responses,
    string Status,
    string SelectedPlayer)
{
    public static BridgePaths Create()
    {
        string root = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "FM-FaceStudio",
            "bridge");
        return new BridgePaths(
            root,
            Path.Combine(root, "commands"),
            Path.Combine(root, "processing"),
            Path.Combine(root, "responses"),
            Path.Combine(root, "status.json"),
            Path.Combine(root, "selected-player.json"));
    }

    public void EnsureCreated()
    {
        Directory.CreateDirectory(Root);
        Directory.CreateDirectory(Commands);
        Directory.CreateDirectory(Processing);
        Directory.CreateDirectory(Responses);
    }
}

internal static class BridgeJson
{
    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true,
        PropertyNameCaseInsensitive = true,
    };
}

internal static class AtomicJson
{
    public static void Write<T>(string destination, T value)
    {
        string directory = Path.GetDirectoryName(destination)
            ?? throw new InvalidOperationException("Destination directory is missing.");
        Directory.CreateDirectory(directory);

        string temporary = destination + ".tmp";
        File.WriteAllText(temporary, JsonSerializer.Serialize(value, BridgeJson.Options));
        File.Move(temporary, destination, overwrite: true);
    }
}
