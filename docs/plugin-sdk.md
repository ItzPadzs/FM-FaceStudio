# FaceStudio Plugin SDK Preview

Alpha 2.0.0 introduces **manifest discovery and validation only**. Third-party plugin code is not automatically executed.

Each plugin lives in its own folder inside the FaceStudio data directory's `plugins` folder and provides:

```text
plugins/
  example-plugin/
    facestudio-plugin.json
    plugin.py
```

Example manifest:

```json
{
  "name": "Example Research Tool",
  "version": "0.1.0",
  "type": "tool",
  "module": "plugin.py",
  "description": "A local research extension."
}
```

The Platform workspace reports whether the manifest is readable and whether the declared module exists. A future reviewed API may expose narrowly scoped extension points. This preview deliberately avoids unrestricted automatic code loading.

Plugins must not claim proprietary Football Manager mesh decoding, `.skin` support, face generation or proprietary export unless those capabilities are independently and lawfully implemented and documented.
