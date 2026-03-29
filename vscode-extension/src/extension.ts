/**
 * AgentLens VS Code Extension — activate/deactivate entry point.
 * Wires together the TreeView, WebView panel, status bar, and auto-refresh.
 */
import * as vscode from "vscode";
import { AgentLensApiClient, TraceRecord } from "./api-client";
import { getConfig, onConfigChange } from "./config";
import { TraceTreeProvider, TraceItem } from "./trace-tree-provider";
import { TraceDetailWebview } from "./trace-detail-webview";
import { AgentLensStatusBar } from "./status-bar";

// Auto-refresh interval in milliseconds
const REFRESH_INTERVAL_MS = 30_000;

export function activate(context: vscode.ExtensionContext): void {
  // ── Bootstrap ────────────────────────────────────────────────────────────
  let config = getConfig();
  let client = new AgentLensApiClient(config.endpoint, config.apiKey);

  const statusBar = new AgentLensStatusBar();
  const treeProvider = new TraceTreeProvider(client);

  // ── Register TreeView ────────────────────────────────────────────────────
  const treeView = vscode.window.createTreeView("agentlens.traces", {
    treeDataProvider: treeProvider,
    showCollapseAll: false,
  });

  // ── Status bar sync: update after each tree refresh ──────────────────────
  // We hook into onDidChangeTreeData to pick up counts post-fetch
  treeProvider.onDidChangeTreeData(() => {
    const traces = treeProvider.getTraces();
    if (traces.length > 0 || !treeProvider.getTraces()) {
      statusBar.update(traces);
    }
  });

  // ── Commands ─────────────────────────────────────────────────────────────

  const refreshCmd = vscode.commands.registerCommand(
    "agentlens.refreshTraces",
    async () => {
      statusBar.reset();
      await treeProvider.refresh();
    },
  );

  const openTraceCmd = vscode.commands.registerCommand(
    "agentlens.openTrace",
    async (item: TraceItem | TraceRecord | undefined) => {
      if (!item) {
        vscode.window.showWarningMessage("AgentLens: no trace selected.");
        return;
      }
      // Handle both TraceItem wrapper and raw TraceRecord from command.arguments
      const trace: TraceRecord = "trace" in item ? (item as TraceItem).trace : item as TraceRecord;
      // Skip synthetic loading/error items
      if (trace.id.startsWith("__")) {
        return;
      }
      await TraceDetailWebview.show(
        context,
        client,
        trace.id,
        config.endpoint,
      );
    },
  );

  // ── React to config changes ───────────────────────────────────────────────
  const configChangeDisposable = onConfigChange(() => {
    config = getConfig();
    client = new AgentLensApiClient(config.endpoint, config.apiKey);
    statusBar.reset();
    treeProvider.updateClient(client);
  });

  // ── Start auto-refresh ────────────────────────────────────────────────────
  treeProvider.startAutoRefresh(REFRESH_INTERVAL_MS);

  // ── Register disposables ──────────────────────────────────────────────────
  context.subscriptions.push(
    treeView,
    refreshCmd,
    openTraceCmd,
    configChangeDisposable,
    statusBar,
    // Ensure timer is cleared when extension is deactivated
    new vscode.Disposable(() => treeProvider.stopAutoRefresh()),
  );
}

export function deactivate(): void {
  // Cleanup is handled through context.subscriptions disposal chain above.
}
