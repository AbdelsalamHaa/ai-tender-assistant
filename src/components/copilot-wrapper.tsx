"use client";

import { useEffect, useState, useRef, createContext, useContext } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AgentState } from "@/lib/types";
import {
  useCoAgent,
  useCopilotChat,
  useFrontendTool,
  useHumanInTheLoop,
  useRenderToolCall,
} from "@copilotkit/react-core";
import { CopilotKitCSSProperties, CopilotSidebar } from "@copilotkit/react-ui";
import { WeatherCard } from "@/components/weather";
import { MoonCard } from "@/components/moon";

// Stable chat ID to persist conversation across page navigations
const CHAT_ID = "enest-main-chat";

// Page configuration with titles and descriptions
const pageConfig: Record<string, { title: string; description: string }> = {
  "/": {
    title: "Home - Proverbs Dashboard",
    description: "The main dashboard with proverbs and general information",
  },
  "/ingest": {
    title: "Document Ingestion",
    description: "Upload and process tender PDF documents",
  },
  "/documents": {
    title: "Tender Document Library",
    description: "View all ingested documents, extracted requirements, and export data",
  },
};

// Valid pages for navigation
const VALID_PAGES = Object.keys(pageConfig);

// Get page title from pathname
function getPageTitle(pathname: string): string {
  return pageConfig[pathname]?.title || `Page: ${pathname}`;
}

// Context-aware suggestions based on current page
function getSuggestionsForPage(pathname: string) {
  const baseSuggestions = [
    {
      title: "Search Documents",
      message: "Search for requirements about transformers in the ingested documents.",
    },
    {
      title: "List Documents",
      message: "What documents have been ingested?",
    },
  ];

  if (pathname === "/") {
    return [
      ...baseSuggestions,
      {
        title: "Generative UI",
        message: "Get the weather in San Francisco.",
      },
      {
        title: "Frontend Tools",
        message: "Set the theme to green.",
      },
      {
        title: "Write Agent State",
        message: "Add a proverb about AI.",
      },
    ];
  }

  if (pathname === "/ingest") {
    return [
      ...baseSuggestions,
      {
        title: "Help with Ingestion",
        message: "How do I upload a tender document?",
      },
      {
        title: "Supported Formats",
        message: "What file formats are supported for ingestion?",
      },
    ];
  }

  if (pathname === "/documents") {
    return [
      ...baseSuggestions,
      {
        title: "Analyze Requirements",
        message: "Summarize all mandatory equipment requirements across documents.",
      },
      {
        title: "Export Help",
        message: "How can I export all requirements to a CSV file?",
      },
      {
        title: "Find Compliance Gaps",
        message: "What requirements have unknown compliance status?",
      },
    ];
  }

  return baseSuggestions;
}

interface CopilotWrapperProps {
  children: React.ReactNode;
}

// Context for sharing state with child components
interface CopilotContextType {
  state: AgentState;
  setState: (state: AgentState) => void;
  themeColor: string;
  setThemeColor: (color: string) => void;
}

const CopilotContext = createContext<CopilotContextType | null>(null);

export function useCopilotContext() {
  const context = useContext(CopilotContext);
  if (!context) {
    throw new Error("useCopilotContext must be used within CopilotWrapper");
  }
  return context;
}

export function CopilotWrapper({ children }: CopilotWrapperProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [themeColor, setThemeColor] = useState("#6366f1");
  const initializedRef = useRef(false);
  const previousPathRef = useRef(pathname);

  // Use stable chat ID to persist conversation
  useCopilotChat({
    id: CHAT_ID,
  });

  // 🪁 Shared State: https://docs.copilotkit.ai/pydantic-ai/shared-state
  const { state, setState } = useCoAgent<AgentState>({
    name: "sample_agent",
    initialState: {
      proverbs: [
        "CopilotKit may be new, but its the best thing since sliced bread.",
      ],
      currentPage: pathname,
      pageTitle: getPageTitle(pathname),
    },
  });

  // Update agent state when page changes (but don't reset on first mount)
  useEffect(() => {
    // Skip if this is the initial mount with same path
    if (!initializedRef.current) {
      initializedRef.current = true;
      previousPathRef.current = pathname;
      return;
    }

    // Only update if path actually changed
    if (previousPathRef.current !== pathname) {
      previousPathRef.current = pathname;
      setState({
        ...state,
        currentPage: pathname,
        pageTitle: getPageTitle(pathname),
      });
    }
  }, [pathname]); // Intentionally not including state/setState to avoid loops

  // 🪁 Frontend Actions: https://docs.copilotkit.ai/pydantic-ai/frontend-actions
  useFrontendTool({
    name: "setThemeColor",
    parameters: [
      {
        name: "themeColor",
        description: "The theme color to set. Make sure to pick nice colors.",
        required: true,
      },
    ],
    handler({ themeColor }) {
      setThemeColor(themeColor);
    },
  });

  // 🪁 Frontend Actions for proverbs
  useFrontendTool({
    name: "updateProverbs",
    parameters: [
      {
        name: "proverbs",
        description: "What the current list of proverbs should be updated to",
        type: "string[]",
        required: true,
      },
    ],
    handler: ({ proverbs }) => {
      setState({
        ...state,
        proverbs: proverbs,
      });
    },
  });

  // 🪁 Frontend Action for page navigation
  useFrontendTool({
    name: "navigateToPage",
    description: `Navigate the user to a different page in the application. 
Available pages:
- "/" (Home): The main dashboard with proverbs
- "/ingest" (Document Ingestion): Upload and process tender PDF documents  
- "/documents" (Document Library): View all ingested documents, extracted requirements, and export data

Use this when the user wants to:
- View or browse documents → navigate to /documents
- Upload a new document → navigate to /ingest
- Go back home → navigate to /`,
    parameters: [
      {
        name: "page",
        description: "The page path to navigate to. Must be one of: '/', '/ingest', '/documents'",
        type: "string",
        required: true,
      },
      {
        name: "reason",
        description: "Brief reason for navigating (shown to user)",
        type: "string",
        required: false,
      },
    ],
    handler: ({ page, reason }: { page: string; reason?: string }) => {
      // Validate the page
      if (!VALID_PAGES.includes(page)) {
        return `Invalid page: ${page}. Valid pages are: ${VALID_PAGES.join(", ")}`;
      }

      // Don't navigate if already on the page
      if (pathname === page) {
        return `Already on ${getPageTitle(page)}`;
      }

      // Navigate to the page
      router.push(page);
      
      const pageTitle = getPageTitle(page);
      return reason 
        ? `Navigating to ${pageTitle}: ${reason}`
        : `Navigating to ${pageTitle}`;
    },
  });

  // 🪁 Generative UI: https://docs.copilotkit.ai/pydantic-ai/generative-ui
  useRenderToolCall(
    {
      name: "get_weather",
      description: "Get the weather for a given location.",
      parameters: [{ name: "location", type: "string", required: true }],
      render: ({ args }) => {
        return <WeatherCard location={args.location} themeColor={themeColor} />;
      },
    },
    [themeColor]
  );

  // 🪁 Human In the Loop: https://docs.copilotkit.ai/pydantic-ai/human-in-the-loop
  useHumanInTheLoop(
    {
      name: "go_to_moon",
      description: "Go to the moon on request.",
      render: ({ respond, status }) => {
        return (
          <MoonCard themeColor={themeColor} status={status} respond={respond} />
        );
      },
    },
    [themeColor]
  );

  const suggestions = getSuggestionsForPage(pathname);

  return (
    <div
      style={
        { "--copilot-kit-primary-color": themeColor } as CopilotKitCSSProperties
      }
    >
      <CopilotSidebar
        defaultOpen={false}
        clickOutsideToClose={false}
        labels={{
          title: "Enest AI Assistant",
          initial: `👋 Hi! I'm your AI assistant. How can I help you today?`,
        }}
        suggestions={suggestions}
      >
        <CopilotContext.Provider value={{ state, setState, themeColor, setThemeColor }}>
          {children}
        </CopilotContext.Provider>
      </CopilotSidebar>
    </div>
  );
}
