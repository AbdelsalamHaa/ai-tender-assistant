"use client";

import { useRouter } from "next/navigation";
import { useCopilotChat } from "@copilotkit/react-core";
import Link from "next/link";

// Capability card component
function CapabilityCard({
  icon,
  title,
  description,
  features,
  action,
  actionLabel,
  gradient,
}: {
  icon: string;
  title: string;
  description: string;
  features: string[];
  action: () => void;
  actionLabel: string;
  gradient: string;
}) {
  return (
    <div
      onClick={action}
      className={`
        group relative overflow-hidden rounded-2xl p-6 cursor-pointer
        bg-zinc-800/50 border border-zinc-700/50
        hover:border-zinc-600 hover:bg-zinc-800/80
        transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl
      `}
    >
      {/* Gradient accent */}
      <div
        className={`absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300 ${gradient}`}
      />

      {/* Icon */}
      <div className="text-4xl mb-4">{icon}</div>

      {/* Title */}
      <h3 className="text-xl font-bold text-white mb-2 group-hover:text-amber-400 transition-colors">
        {title}
      </h3>

      {/* Description */}
      <p className="text-zinc-400 text-sm mb-4 leading-relaxed">{description}</p>

      {/* Features */}
      <ul className="space-y-2 mb-6">
        {features.map((feature, idx) => (
          <li key={idx} className="flex items-center gap-2 text-sm text-zinc-300">
            <span className="text-amber-500">✓</span>
            {feature}
          </li>
        ))}
      </ul>

      {/* Action button */}
      <div
        className={`
          inline-flex items-center gap-2 px-4 py-2 rounded-lg
          bg-gradient-to-r ${gradient} text-white font-medium text-sm
          group-hover:shadow-lg transition-all
        `}
      >
        {actionLabel}
        <span className="group-hover:translate-x-1 transition-transform">→</span>
      </div>
    </div>
  );
}

// Stats component
function StatCard({ value, label, icon }: { value: string; label: string; icon: string }) {
  return (
    <div className="text-center">
      <div className="text-3xl mb-1">{icon}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-sm text-zinc-400">{label}</div>
    </div>
  );
}

export default function HomePage() {
  const router = useRouter();
  const { reset } = useCopilotChat();

  const openChat = () => {
    // Find and click the sidebar toggle button
    const sidebarButton = document.querySelector('[data-copilotkit-sidebar-toggle]') as HTMLButtonElement;
    if (sidebarButton) {
      sidebarButton.click();
    }
  };

  return (
    <div className="min-h-screen bg-zinc-900 text-white">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-amber-500/10 via-zinc-900 to-purple-500/10" />
        
        {/* Animated grid pattern */}
        <div
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `
              linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
              linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
            `,
            backgroundSize: "50px 50px",
          }}
        />

        <div className="relative max-w-6xl mx-auto px-6 py-20">
          {/* Badge */}
          <div className="flex justify-center mb-8">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/30">
              <span className="text-amber-400 text-sm font-medium">🚀 Powered by AI</span>
            </div>
          </div>

          {/* Main heading */}
          <h1 className="text-5xl md:text-7xl font-bold text-center mb-6 leading-tight">
            <span className="text-white">AI Tender</span>
            <br />
            <span className="bg-gradient-to-r from-amber-400 via-orange-500 to-red-500 bg-clip-text text-transparent">
              Assistant
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-xl text-zinc-400 text-center max-w-2xl mx-auto mb-12 leading-relaxed">
            Automatically extract, analyze, and manage requirements from tender documents.
            Save hours of manual work with intelligent document processing.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-wrap justify-center gap-4 mb-16">
            <Link
              href="/ingest"
              className="px-8 py-4 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-zinc-900 font-bold rounded-xl transition-all hover:scale-105 hover:shadow-xl hover:shadow-amber-500/20"
            >
              📄 Upload Tender Document
            </Link>
            <Link
              href="/documents"
              className="px-8 py-4 bg-zinc-800 hover:bg-zinc-700 text-white font-medium rounded-xl border border-zinc-700 hover:border-zinc-600 transition-all hover:scale-105"
            >
              📚 View Document Library
            </Link>
          </div>

          {/* Stats */}
          <div className="flex justify-center gap-12 flex-wrap">
            <StatCard icon="📋" value="100+" label="Requirements per doc" />
            <StatCard icon="⚡" value="90%" label="Time saved" />
            <StatCard icon="🎯" value="99%" label="Extraction accuracy" />
          </div>
        </div>
      </section>

      {/* Capabilities Section */}
      <section className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Everything you need for tender management
            </h2>
            <p className="text-zinc-400 max-w-2xl mx-auto">
              From document upload to requirements analysis, our AI-powered platform handles it all.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Document Ingestion */}
            <CapabilityCard
              icon="📤"
              title="Document Ingestion"
              description="Upload tender PDFs and let our AI automatically process them in the background."
              features={[
                "PDF parsing & text extraction",
                "Automatic metadata detection",
                "Background processing with Celery",
                "Real-time status updates",
              ]}
              action={() => router.push("/ingest")}
              actionLabel="Upload Document"
              gradient="from-blue-500 to-cyan-500"
            />

            {/* Requirements Extraction */}
            <CapabilityCard
              icon="🎯"
              title="Requirements Extraction"
              description="AI automatically identifies and categorizes every requirement in your tender documents."
              features={[
                "Equipment specifications",
                "Compliance requirements",
                "Timeline & deadlines",
                "Mandatory vs Optional classification",
              ]}
              action={() => router.push("/documents")}
              actionLabel="View Requirements"
              gradient="from-amber-500 to-orange-500"
            />

            {/* Semantic Search */}
            <CapabilityCard
              icon="🔍"
              title="Semantic Search"
              description="Find relevant information across all documents using natural language queries."
              features={[
                "AI-powered semantic matching",
                "Search across all documents",
                "Find similar requirements",
                "Context-aware results",
              ]}
              action={openChat}
              actionLabel="Try Search"
              gradient="from-purple-500 to-pink-500"
            />

            {/* AI Chat Assistant */}
            <CapabilityCard
              icon="💬"
              title="AI Chat Assistant"
              description="Get instant answers about your documents with our intelligent chat assistant."
              features={[
                "Natural language queries",
                "Document analysis",
                "Requirements summarization",
                "Navigation assistance",
              ]}
              action={openChat}
              actionLabel="Open Chat"
              gradient="from-green-500 to-emerald-500"
            />

            {/* Export & Reports */}
            <CapabilityCard
              icon="📊"
              title="Export & Reports"
              description="Export requirements to CSV or JSON for further analysis and compliance tracking."
              features={[
                "CSV export with all fields",
                "JSON export for integration",
                "Filter by category",
                "Compliance status tracking",
              ]}
              action={() => router.push("/documents")}
              actionLabel="Export Data"
              gradient="from-red-500 to-rose-500"
            />

            {/* Compliance Tracking */}
            <CapabilityCard
              icon="✅"
              title="Compliance Tracking"
              description="Track your compliance status against extracted requirements."
              features={[
                "Yes/No/Partial status",
                "Category breakdown",
                "Mandatory requirement alerts",
                "Gap analysis",
              ]}
              action={() => router.push("/documents")}
              actionLabel="Track Compliance"
              gradient="from-indigo-500 to-violet-500"
            />
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-20 px-6 bg-zinc-800/30">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              How it works
            </h2>
            <p className="text-zinc-400 max-w-2xl mx-auto">
              Three simple steps to transform your tender document management
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {/* Step 1 */}
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gradient-to-r from-amber-500 to-orange-500 flex items-center justify-center text-2xl font-bold text-zinc-900">
                1
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Upload</h3>
              <p className="text-zinc-400">
                Drop your tender PDF documents into our secure upload system. Processing starts immediately.
              </p>
            </div>

            {/* Step 2 */}
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center text-2xl font-bold text-white">
                2
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Extract</h3>
              <p className="text-zinc-400">
                Our AI reads every page, identifies requirements, and categorizes them automatically.
              </p>
            </div>

            {/* Step 3 */}
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gradient-to-r from-green-500 to-emerald-500 flex items-center justify-center text-2xl font-bold text-white">
                3
              </div>
              <h3 className="text-xl font-bold text-white mb-3">Analyze</h3>
              <p className="text-zinc-400">
                Search, filter, export, and track compliance. Chat with AI to get instant answers.
              </p>
            </div>
          </div>

          {/* CTA */}
          <div className="text-center mt-12">
            <Link
              href="/ingest"
              className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-zinc-900 font-bold rounded-xl transition-all hover:scale-105"
            >
              Get Started Now
              <span>→</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-zinc-800">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="text-zinc-400 text-sm">
              <span className="text-amber-500 font-bold">AI Tender Assistant</span>
            </div>
            <nav className="flex gap-6 text-sm">
              <Link href="/" className="text-amber-500">
                Home
              </Link>
              <Link href="/ingest" className="text-zinc-400 hover:text-white transition-colors">
                Upload
              </Link>
              <Link href="/documents" className="text-zinc-400 hover:text-white transition-colors">
                Documents
              </Link>
            </nav>
          </div>
        </div>
      </footer>
    </div>
  );
}
