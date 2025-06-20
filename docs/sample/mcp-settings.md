こちらはサンプルドキュメントです。

```
{
    "mcpServers": {
        "docs-mcp": {
            "command": "uv",
            "args": [
                "run",
                "--directory",
                "/path/to/docs-mcp/src",
                "docs_mcp.py"
            ],
        }
    }
}
```

このように設定したjsonを作成することで、Claude Desktop, Claude Code, Cursorなどで使用できます。

## Claude Desktop
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

※jsonを記述する際、Windowsパスではバックスラッシュを二重にする（\）必要があります

## Claude Code
プロジェクトルートに `.mcp.json` ファイルを作成したのち、`claude`コマンド実行後許可すると使えます。