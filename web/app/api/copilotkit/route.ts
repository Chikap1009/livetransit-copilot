import { HttpAgent } from '@ag-ui/client';
import {
  CopilotRuntime,
  EmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from '@copilotkit/runtime';
import { NextRequest } from 'next/server';

// Bridge CopilotKit to our Python Pydantic AI agent over the AG-UI protocol.
const runtime = new CopilotRuntime({
  agents: {
    livetransit: new HttpAgent({ url: 'http://localhost:8000/agent/ag-ui' }),
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter: new EmptyAdapter(),
    endpoint: '/api/copilotkit',
  });
  return handleRequest(req);
};
