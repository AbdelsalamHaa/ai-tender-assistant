import type { Metadata } from "next";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotWrapper } from "@/components/copilot-wrapper";
import "./globals.css";
import "@copilotkit/react-ui/styles.css";

export const metadata: Metadata = {
  title: "Enest - Tender Document Management",
  description: "AI-powered tender document management and requirements extraction",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <CopilotKit runtimeUrl="/api/copilotkit" agent="sample_agent">
          <CopilotWrapper>{children}</CopilotWrapper>
        </CopilotKit>
      </body>
    </html>
  );
}
