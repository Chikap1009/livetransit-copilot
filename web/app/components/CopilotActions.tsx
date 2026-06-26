'use client';

import { useCopilotAction } from '@copilotkit/react-core';
import type { CSSProperties } from 'react';

function pill(done: boolean): CSSProperties {
  return {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    background: done ? '#eef2f7' : '#fff7e6',
    color: done ? '#3a4a5a' : '#8a5a00',
    border: `1px solid ${done ? '#dde3ec' : '#ffe1a6'}`,
    borderRadius: 14, padding: '4px 10px', margin: '4px 0',
    font: '12px system-ui, sans-serif', whiteSpace: 'nowrap',
  };
}

/**
 * Catch-all renderer for the agent's tool calls: shows a clean status pill
 * ("calling X…" -> "✓ X") instead of CopilotKit's default raw JSON card.
 * Registers the renderer with CopilotKit; renders nothing itself.
 */
export default function CopilotActions() {
  useCopilotAction({
    name: '*',
    render: ({ name, status }: { name: string; status: string }) => {
      const done = status === 'complete';
      return (
        <div style={pill(done)}>
          {done ? '✓' : '🔧'} {done ? name : `calling ${name}…`}
        </div>
      );
    },
  });

  return null;
}
