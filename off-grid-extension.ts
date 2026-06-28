/**
 * Cubiczan Tool Extension for Off Grid Mobile
 *
 * Dropping this file into Off Grid's pro/ directory and registering it
 * via the tool extension system makes Cubiczan agents a first-class
 * capability in the mobile app.
 *
 * Usage:
 *   import { cubiczanExtension } from './cubiczanExtension';
 *   import { registerToolExtension } from '../services/tools/extensions';
 *   registerToolExtension(cubiczanExtension);
 *
 * Or if using pro package:
 *   // In pro/activate.ts:
 *   activate({ registerToolExtension }) {
 *     registerToolExtension(cubiczanExtension);
 *   }
 */

import type { ToolExtension, ToolCall, ToolResult, ToolDefinition } from '../services/tools/types';

const CUBICZAN_HOST = process.env.CUBICZAN_MCP_HOST || 'http://localhost:8080';

const CUBICZAN_TOOLS: ToolDefinition[] = [
  {
    id: 'cubiczan_analyze',
    name: 'cubiczan_analyze',
    displayName: 'Cubiczan Analyze',
    description:
      'Run Cubiczan multi-agent analysis on a business or technical problem. Agents examine from finance, supply-chain, compliance, and engineering perspectives.',
    icon: 'activity',
    requiresNetwork: true,
    parameters: {
      problem: {
        type: 'string',
        description: 'The problem or question to analyze',
        required: true,
      },
      perspectives: {
        type: 'string',
        description: 'Comma-separated perspectives: finance, supply_chain, compliance, engineering, strategy',
      },
    },
  },
  {
    id: 'cubiczan_consensus',
    name: 'cubiczan_consensus',
    displayName: 'CHP Consensus',
    description:
      'Run CHP (Consensus Hardening Protocol) governance on a proposal. Returns R0 gate status and adversarial attack analysis.',
    icon: 'shield',
    requiresNetwork: true,
    parameters: {
      proposal: {
        type: 'string',
        description: 'The proposal or decision to evaluate',
        required: true,
      },
      domain: {
        type: 'string',
        description: 'Domain: finance, supply_chain, compliance, product, strategy',
      },
    },
  },
  {
    id: 'cubiczan_swarm',
    name: 'cubiczan_swarm',
    displayName: 'Cubiczan Swarm',
    description:
      'Deploy a stigmergic agent swarm to monitor a topic, market, or data source. Returns swarm ID and observations.',
    icon: 'radio',
    requiresNetwork: true,
    parameters: {
      topic: {
        type: 'string',
        description: 'What to monitor',
        required: true,
      },
      data_sources: {
        type: 'string',
        description: 'Comma-separated: news, social, regulatory, market, patents',
      },
      interval: {
        type: 'string',
        description: 'Check frequency: realtime, hourly, daily, weekly',
      },
    },
  },
];

/**
 * Parse tool calls from model-generated text.
 * Off Grid models output tool calls in various formats (JSON, function-call,
 * XML-style). This extension parses Cubiczan-specific call formats.
 */
function parseCubiczanToolCall(text: string, idSuffix: number): ToolCall | null {
  // Standard JSON: {"name": "tool", "arguments": {...}}
  try {
    const parsed = JSON.parse(text);
    const name = parsed.name || parsed.tool;
    if (name && CUBICZAN_TOOLS.some(t => t.name === name)) {
      return {
        id: `cubiczan-tc-${Date.now()}-${idSuffix}`,
        name,
        arguments: parsed.arguments || parsed.parameters || {},
      };
    }
  } catch {
    // Continue to other formats
  }

  // Cubiczan-specific format: tool_name("query": "...")
  for (const tool of CUBICZAN_TOOLS) {
    const pattern = new RegExp(`^${tool.name}\\s*\\(([\\s\\S]*)\\)$`);
    const match = text.match(pattern);
    if (match) {
      try {
        const args = JSON.parse(`{${match[1]}}`);
        return {
          id: `cubiczan-tc-${Date.now()}-${idSuffix}`,
          name: tool.name,
          arguments: args,
        };
      } catch {
        // fall through
      }
    }
  }

  return null;
}

/**
 * Execute a Cubiczan tool by calling the MCP server.
 */
async function executeCubiczanTool(call: ToolCall): Promise<ToolResult> {
  const start = Date.now();
  const apiKey = await getCubiczanApiKey();

  try {
    const response = await fetch(`${CUBICZAN_HOST}/v1/tools/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
      },
      body: JSON.stringify({
        name: call.name,
        arguments: call.arguments,
      }),
    });

    if (!response.ok) {
      throw new Error(`Cubiczan server error: ${response.status}`);
    }

    const data = await response.json();
    return {
      toolCallId: call.id,
      name: call.name,
      content: data.content || JSON.stringify(data),
      durationMs: Date.now() - start,
    };
  } catch (error: any) {
    return {
      toolCallId: call.id,
      name: call.name,
      content: '',
      error: error.message || 'Failed to execute Cubiczan tool',
      durationMs: Date.now() - start,
    };
  }
}

/**
 * Get the stored Cubiczan API key (from keychain/async storage).
 * Falls back to a placeholder for local/dev use.
 */
async function getCubiczanApiKey(): Promise<string | null> {
  try {
    // In Off Grid Pro, API keys are stored in the system keychain
    const Keychain = require('react-native-keychain');
    const credentials = await Keychain.getGenericPassword({ service: 'cubiczan-mcp' });
    return credentials ? credentials.password : null;
  } catch {
    // Fall back to AsyncStorage for non-Pro builds
    try {
      const AsyncStorage = require('@react-native-async-storage/async-storage').default;
      return await AsyncStorage.getItem('cubiczan_api_key');
    } catch {
      return null;
    }
  }
}

export const cubiczanExtension: ToolExtension = {
  id: 'cubiczan',

  getSystemPromptHint(): string {
    return (
      '\n\n' +
      'Cubiczan multi-agent intelligence is available. You can:\n' +
      '- Analyze problems using cubiczan_analyze (multi-perspective agent analysis)\n' +
      '- Run governance consensus using cubiczan_consensus (CHP protocol)\n' +
      '- Deploy monitoring swarms using cubiczan_swarm (stigmergic coordination)\n' +
      'When a user asks about analysis, governance, or monitoring, use these tools proactively.'
    );
  },

  getToolDefinitions(): ToolDefinition[] {
    return CUBICZAN_TOOLS;
  },

  parseToolCalls(text: string): ToolCall[] {
    const calls: ToolCall[] = [];
    let idSuffix = 0;

    // Try each line
    const lines = text.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;

      const call = parseCubiczanToolCall(trimmed, idSuffix);
      if (call) {
        calls.push(call);
        idSuffix++;
      }
    }

    return calls;
  },

  stripFromVisibleText(text: string): string {
    // Remove any Cubiczan tool call lines from visible output
    const lines = text.split('\n');
    const filtered = lines.filter((line) => {
      const trimmed = line.trim();
      return !CUBICZAN_TOOLS.some((t) => trimmed.startsWith(t.name + '('));
    });
    return filtered.join('\n');
  },

  canHandle(toolName: string): boolean {
    return CUBICZAN_TOOLS.some((t) => t.name === toolName);
  },

  async execute(call: ToolCall): Promise<ToolResult> {
    return executeCubiczanTool(call);
  },

  enabledToolCount(): number {
    // In a real integration, check which Cubiczan servers are configured
    return CUBICZAN_TOOLS.length;
  },
};
