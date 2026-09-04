using System.Text.RegularExpressions;
using BepInEx.Logging;
using Il2CppInterop.Runtime.Injection;
using UnityEngine;
using UnityEngine.UIElements;

namespace FMFaceStudioBridge;

internal sealed class SelectionProbe : MonoBehaviour
{
    private static readonly Regex ExplicitId = new(
        @"(?:\bID\b\s*[:#]?\s*|\()(?<id>\d{5,12})\)?",
        RegexOptions.Compiled | RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

    private static readonly Regex BracketId = new(
        @"\[(?<id>\d{5,12})\]",
        RegexOptions.Compiled | RegexOptions.CultureInvariant);

    private ManualLogSource? _log;
    private Action<PlayerSelection>? _onSelection;
    private float _nextScan;
    private long _lastId;
    private string _lastName = string.Empty;

    public static void Register() => ClassInjector.RegisterTypeInIl2Cpp<SelectionProbe>();

    public void Configure(ManualLogSource log, Action<PlayerSelection> onSelection)
    {
        _log = log;
        _onSelection = onSelection;
    }

    private void Update()
    {
        if (Time.unscaledTime < _nextScan)
        {
            return;
        }

        _nextScan = Time.unscaledTime + 0.75f;
        try
        {
            ScanActiveUi();
        }
        catch (Exception exception)
        {
            _log?.LogDebug($"Selection probe scan skipped: {exception.GetType().Name}: {exception.Message}");
        }
    }

    private void ScanActiveUi()
    {
        UIDocument[] documents = Resources.FindObjectsOfTypeAll<UIDocument>();
        if (documents.Length == 0)
        {
            return;
        }

        List<UiText> texts = new(256);
        foreach (UIDocument document in documents)
        {
            VisualElement? root = document?.rootVisualElement;
            if (root is null || root.panel is null || !root.visible)
            {
                continue;
            }

            CollectText(root, texts, 0);
        }

        Candidate? candidate = FindCandidate(texts);
        if (candidate is null || candidate.Id == _lastId && candidate.Name == _lastName)
        {
            return;
        }

        _lastId = candidate.Id;
        _lastName = candidate.Name;
        PlayerSelection selection = new(
            candidate.Id,
            candidate.Name,
            candidate.Club,
            candidate.Nation,
            "fm26-ui-probe",
            DateTimeOffset.UtcNow);

        _log?.LogInfo($"Selected player detected: {selection.Name} [{selection.Id}]");
        _onSelection?.Invoke(selection);
    }

    private static void CollectText(VisualElement element, List<UiText> output, int depth)
    {
        if (depth > 40 || !element.visible)
        {
            return;
        }

        string? value = element switch
        {
            Label label => label.text,
            TextElement textElement => textElement.text,
            _ => null,
        };

        if (!string.IsNullOrWhiteSpace(value))
        {
            output.Add(new UiText(
                Normalize(value),
                element.name ?? string.Empty,
                element.worldBound.x,
                element.worldBound.y,
                element.worldBound.width,
                element.worldBound.height));
        }

        for (int index = 0; index < element.childCount; index++)
        {
            CollectText(element[index], output, depth + 1);
        }
    }

    private static Candidate? FindCandidate(IReadOnlyList<UiText> texts)
    {
        List<(long Id, UiText Text)> ids = new();
        foreach (UiText text in texts)
        {
            Match match = ExplicitId.Match(text.Value);
            if (!match.Success)
            {
                match = BracketId.Match(text.Value);
            }

            if (match.Success && long.TryParse(match.Groups["id"].Value, out long id) && id > 0)
            {
                ids.Add((id, text));
            }
        }

        foreach ((long id, UiText idText) in ids.OrderBy(item => item.Text.Y))
        {
            string? inlineName = ExtractInlineName(idText.Value);
            string? nearbyName = inlineName ?? FindNearbyName(texts, idText);
            if (!IsLikelyPlayerName(nearbyName))
            {
                continue;
            }

            string? club = FindNearbyMetadata(texts, idText, new[] { "club", "team" });
            string? nation = FindNearbyMetadata(texts, idText, new[] { "nation", "nationality", "country" });
            return new Candidate(id, nearbyName!, club, nation);
        }

        return null;
    }

    private static string? ExtractInlineName(string value)
    {
        int idIndex = value.IndexOf("ID", StringComparison.OrdinalIgnoreCase);
        if (idIndex <= 0)
        {
            int bracketIndex = value.IndexOf('[');
            idIndex = bracketIndex > 0 ? bracketIndex : -1;
        }

        return idIndex > 0 ? CleanName(value[..idIndex]) : null;
    }

    private static string? FindNearbyName(IReadOnlyList<UiText> texts, UiText idText)
    {
        return texts
            .Where(text => text.Value != idText.Value)
            .Where(text => Math.Abs(text.Y - idText.Y) < 150f)
            .Where(text => Math.Abs(text.X - idText.X) < 650f)
            .OrderBy(text => Distance(text, idText))
            .Select(text => CleanName(text.Value))
            .FirstOrDefault(IsLikelyPlayerName);
    }

    private static string? FindNearbyMetadata(IReadOnlyList<UiText> texts, UiText idText, string[] hints)
    {
        return texts
            .Where(text => Math.Abs(text.Y - idText.Y) < 260f)
            .Where(text => Math.Abs(text.X - idText.X) < 900f)
            .Where(text => hints.Any(hint => text.Name.Contains(hint, StringComparison.OrdinalIgnoreCase)))
            .OrderBy(text => Distance(text, idText))
            .Select(text => text.Value)
            .FirstOrDefault(value => !string.IsNullOrWhiteSpace(value));
    }

    private static bool IsLikelyPlayerName(string? value)
    {
        if (string.IsNullOrWhiteSpace(value) || value.Length < 3 || value.Length > 80)
        {
            return false;
        }

        if (value.Any(char.IsDigit) || value.Contains(':') || value.Contains('/'))
        {
            return false;
        }

        string[] excluded =
        {
            "overview", "personal", "performance", "career", "messages", "continue",
            "squad", "portal", "player report", "attributes", "contract", "comparison"
        };
        return !excluded.Any(item => value.Equals(item, StringComparison.OrdinalIgnoreCase));
    }

    private static string? CleanName(string value)
    {
        string cleaned = Regex.Replace(value, @"\s+", " ").Trim(' ', '-', '–', '—', '(', ')');
        return string.IsNullOrWhiteSpace(cleaned) ? null : cleaned;
    }

    private static string Normalize(string value) => Regex.Replace(value, @"\s+", " ").Trim();

    private static float Distance(UiText first, UiText second)
    {
        float dx = first.X - second.X;
        float dy = first.Y - second.Y;
        return dx * dx + dy * dy;
    }

    private sealed record UiText(string Value, string Name, float X, float Y, float Width, float Height);
    private sealed record Candidate(long Id, string Name, string? Club, string? Nation);
}
