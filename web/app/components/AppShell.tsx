'use client';

import { CopilotKit } from '@copilotkit/react-core';
import { CopilotSidebar } from '@copilotkit/react-ui';
import '@copilotkit/react-ui/styles.css';

import LiveMap from './LiveMap';

export default function AppShell() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit" agent="livetransit">
      <LiveMap />
      <CopilotSidebar
        defaultOpen
        labels={{
          title: 'LiveTransit Copilot',
          initial: 'Ask me about routes, arrivals, or service alerts.',
        }}
      />
    </CopilotKit>
  );
}
