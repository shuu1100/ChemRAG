import React, { useEffect, useState } from 'react';
import { CitationBadge } from '../components/citations/CitationBadge';
import { chatApi } from '../services/api';
import { AgentStepTrace, ChatMessage, CitationItem } from '../types';

export const ChatPage: React.FC = () => {
  const [conversationId, setConversationId] = useState<string>(() => {
    return localStorage.getItem('chemrag_current_conversation') || `conv-${Date.now()}`;
  });

  const [inputMessage, setInputMessage] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const initialWelcomeMsg: ChatMessage = {
    id: 'msg-welcome',
    sender: 'assistant',
    content:
      'Welcome to **ChemRAG**. Ask any chemical research, thermodynamic property, or synthesis question. All answers are grounded in literature with verified citation tags `[CIT-001]`.',
    timestamp: new Date().toLocaleTimeString(),
    confidence_score: 1.0,
    chemistry_validated: true,
  };

  const [messages, setMessages] = useState<ChatMessage[]>([initialWelcomeMsg]);
  const [activeTrace, setActiveTrace] = useState<AgentStepTrace[] | null>(null);

  useEffect(() => {
    localStorage.setItem('chemrag_current_conversation', conversationId);
  }, [conversationId]);

  const handleSendMessage = async () => {
    const trimmed = inputMessage.trim();
    if (!trimmed || isLoading) return;

    setErrorMessage(null);
    setIsLoading(true);

    const userMsg: ChatMessage = {
      id: `msg-user-${Date.now()}`,
      sender: 'user',
      content: trimmed,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');

    try {
      const data = await chatApi.sendQuery(trimmed, conversationId);

      const assistantCitations: CitationItem[] = (data.citations || []).map((c: any) => ({
        citation_id: c.citation_id,
        chunk_id: c.chunk_id,
        document_id: c.document_id,
        document_title: c.document_title,
        page_number: c.page_number,
        confidence: c.confidence,
        raw_text: c.raw_text,
      }));

      const assistantTrace: AgentStepTrace[] = (data.agent_trace || []).map((t: any) => ({
        agent_name: t.agent_name,
        status: t.status,
        timestamp: t.timestamp,
        summary: t.summary,
      }));

      const assistantMsg: ChatMessage = {
        id: `msg-ast-${data.run_id || Date.now()}`,
        sender: 'assistant',
        content: data.answer || 'No response generated.',
        timestamp: data.timestamp || new Date().toLocaleTimeString(),
        confidence_score: data.confidence || 0.85,
        chemistry_validated: Boolean(data.chemistry_validated),
        contained_entities: data.contained_entities || [],
        citations: assistantCitations,
        agent_trace: assistantTrace,
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setActiveTrace(assistantTrace);
      setActiveRunId(data.run_id || null);
    } catch (err: any) {
      console.error('Chat API request error:', err);
      const errDetail = err?.response?.data?.detail || err?.message || 'Failed to connect to ChemRAG Assistant.';
      setErrorMessage(`Request Failed: ${errDetail}`);

      const errBotMsg: ChatMessage = {
        id: `msg-err-${Date.now()}`,
        sender: 'assistant',
        content: `⚠️ **Error Processing Query**: ${errDetail}\n\nPlease check server connectivity or LLM provider credentials.`,
        timestamp: new Date().toLocaleTimeString(),
        confidence_score: 0.0,
        chemistry_validated: false,
      };
      setMessages((prev) => [...prev, errBotMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFetchTrace = async (runId?: string, fallbackTrace?: AgentStepTrace[]) => {
    if (!runId) {
      if (fallbackTrace) setActiveTrace(fallbackTrace);
      return;
    }

    try {
      const data = await chatApi.getTrace(runId);
      if (data && data.agent_trace) {
        setActiveTrace(data.agent_trace);
        setActiveRunId(runId);
      } else if (fallbackTrace) {
        setActiveTrace(fallbackTrace);
      }
    } catch (err) {
      console.warn('Trace fetch API warning:', err);
      if (fallbackTrace) setActiveTrace(fallbackTrace);
    }
  };

  const handleNewResearchQuery = () => {
    const newConvId = `conv-${Date.now()}`;
    setConversationId(newConvId);
    setMessages([initialWelcomeMsg]);
    setActiveTrace(null);
    setActiveRunId(null);
    setInputMessage('');
    setErrorMessage(null);
  };

  return (
    <div className="flex h-[calc(100vh-6rem)] gap-6 max-w-7xl mx-auto select-none">
      {/* Main Chat Container */}
      <div className="flex-1 flex flex-col bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        {/* Chat Header */}
        <div className="px-6 py-3.5 bg-slate-950 border-b border-slate-800 flex justify-between items-center">
          <div>
            <h3 className="text-sm font-extrabold text-white flex items-center gap-2">
              💬 ChemRAG Scientific Assistant
            </h3>
            <p className="text-[11px] text-slate-400">
              Strict evidence grounding • Session ID: <code className="font-mono text-cyan-400">{conversationId}</code>
            </p>
          </div>

          <button
            onClick={handleNewResearchQuery}
            type="button"
            className="px-3.5 py-1.5 text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-all flex items-center gap-1.5 shadow-sm"
          >
            <span>✨</span>
            <span>New Research Query</span>
          </button>
        </div>

        {/* Error Alert Bar */}
        {errorMessage && (
          <div className="px-6 py-2.5 bg-rose-950/80 border-b border-rose-800/80 text-rose-300 text-xs font-mono flex items-center justify-between">
            <span>{errorMessage}</span>
            <button onClick={() => setErrorMessage(null)} className="text-rose-400 hover:text-white text-xs font-bold">
              ✕
            </button>
          </div>
        )}

        {/* Message Feed */}
        <div className="flex-1 p-6 overflow-y-auto space-y-6">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-3xl p-4 rounded-2xl text-xs leading-relaxed space-y-3 ${
                  msg.sender === 'user'
                    ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-br-none shadow-md font-medium'
                    : 'bg-slate-950 border border-slate-800 text-slate-200 rounded-bl-none shadow-md'
                }`}
              >
                {/* Message Body */}
                <div className="whitespace-pre-wrap font-sans">{msg.content}</div>

                {/* Metadata Badges & Citations for Assistant */}
                {msg.sender === 'assistant' && (
                  <div className="pt-3 border-t border-slate-800/80 space-y-2">
                    {/* Citations Row */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px]">
                        <span className="text-slate-400 text-[10px] uppercase font-bold">Citations:</span>
                        {msg.citations.map((cit) => (
                          <CitationBadge
                            key={cit.citation_id}
                            citationId={cit.citation_id}
                            documentTitle={cit.document_title}
                            pageNumber={cit.page_number}
                            confidence={cit.confidence}
                          />
                        ))}
                      </div>
                    )}

                    {/* Confidence & Chemistry Verification */}
                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                      <div className="flex items-center gap-3">
                        {msg.confidence_score !== undefined && (
                          <span title="Retrieval & Synthesis Confidence">
                            Confidence: <strong className="text-cyan-400">{(msg.confidence_score * 100).toFixed(1)}%</strong>
                          </span>
                        )}
                        {msg.chemistry_validated && (
                          <span className="text-emerald-400 font-bold" title="RDKit / PubChem Structure Verified">
                            ✓ Chemistry Validated
                          </span>
                        )}
                      </div>

                      {msg.agent_trace && (
                        <button
                          onClick={() => handleFetchTrace(activeRunId || undefined, msg.agent_trace)}
                          className="text-cyan-400 hover:underline font-bold"
                        >
                          View Agent Trace ({msg.agent_trace.length})
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <span className="text-[10px] text-slate-500 font-mono mt-1 px-1">{msg.timestamp}</span>
            </div>
          ))}

          {/* Loading Synthesizing Indicator */}
          {isLoading && (
            <div className="flex flex-col items-start">
              <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 text-xs text-cyan-400 font-mono flex items-center gap-3 shadow-md">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
                <span>Synthesizing evidence-backed answer via Multi-Agent RAG Pipeline...</span>
              </div>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="p-4 bg-slate-950 border-t border-slate-800 flex gap-3">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !isLoading && handleSendMessage()}
            disabled={isLoading}
            placeholder={
              isLoading
                ? 'Processing query across agent graph...'
                : 'Ask a scientific research question (e.g. Ethanol heat of vaporization, CAS 64-17-5)...'
            }
            className="flex-1 px-4 py-3 text-xs bg-slate-900 border border-slate-700 rounded-xl text-slate-100 focus:outline-none focus:border-cyan-500 disabled:opacity-50 font-sans"
          />
          <button
            onClick={handleSendMessage}
            disabled={isLoading || !inputMessage.trim()}
            className="px-6 py-3 text-xs font-bold text-slate-950 bg-cyan-400 hover:bg-cyan-300 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl shadow-lg shadow-cyan-500/20 font-mono transition-all"
          >
            {isLoading ? 'Processing...' : 'Send 🚀'}
          </button>
        </div>
      </div>

      {/* Agent Trace Drawer / Panel */}
      <div className="w-80 bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col gap-4 shadow-xl overflow-y-auto">
        <div className="border-b border-slate-800 pb-3 flex justify-between items-center">
          <div>
            <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <span>🤖</span> Safe Agent Trace
            </h4>
            <p className="text-[10px] text-slate-400 mt-0.5">Operational pipeline status (No hidden chain-of-thought)</p>
          </div>
          {activeTrace && (
            <button
              onClick={() => setActiveTrace(null)}
              className="text-slate-400 hover:text-slate-200 text-xs font-bold px-2 py-1 rounded bg-slate-950 border border-slate-800"
            >
              Close
            </button>
          )}
        </div>

        {!activeTrace ? (
          <div className="text-center py-12 text-xs text-slate-500 font-mono space-y-2">
            <div>Select a message or submit a query to view real operational trace stages.</div>
          </div>
        ) : (
          <div className="space-y-3 font-mono text-xs">
            {activeTrace.map((step, i) => (
              <div key={i} className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-cyan-400 text-[11px]">{step.agent_name}</span>
                  <span
                    className={`px-1.5 py-0.5 text-[9px] rounded uppercase font-bold border ${
                      step.status === 'completed'
                        ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                        : step.status === 'blocked' || step.status === 'failed'
                        ? 'bg-rose-950 text-rose-400 border-rose-800'
                        : 'bg-amber-950 text-amber-400 border-amber-800 animate-pulse'
                    }`}
                  >
                    {step.status}
                  </span>
                </div>
                <p className="text-[11px] text-slate-300 leading-snug">{step.summary}</p>
                <div className="text-[9px] text-slate-500 text-right">{step.timestamp}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatPage;
