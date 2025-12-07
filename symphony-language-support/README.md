# Symphony Language Support

This extension provides basic syntax highlighting for the Symphony modelling language in Visual Studio Code.

## Features

- Syntax highlighting for:
  - Keywords such as `sum`, `prod`, `domain`, `member`, `category`, `dimension`, `parameter`, `variable`, `unit`, `deviation_unit`, `equation`, `logged`, `intertemporal`
  - Booleans (`True`, `False`)
  - Numbers
  - Brackets and operators
  - Identifiers
  - Line comments starting with `#` or `//`
  - Triple-quoted and double-quoted strings

## Installation (from this folder)

1. Install `vsce` if you do not already have it:

   ```bash
   npm install -g @vscode/vsce
   ```

2. In this extension folder, run:

   ```bash
   vsce package
   ```

   This will create a `.vsix` file.

3. In Visual Studio Code, use the command palette:
   - `Extensions: Install from VSIX...`
   - Select the generated `.vsix` file.

4. Open a `.sym` file and the Symphony syntax highlighting will be active.
