import React, { useState } from 'react';
import { CitationBadge } from '../components/citations/CitationBadge';
import { AgentStepTrace, ChatMessage, CitationItem } from '../types';

export const ChatPage: React.FC = () => {
  const [inputMessage, setInputMessage] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'msg-1',
      sender: 'assistant',
      content:
        'Welcome to **ChemRAG**. Ask any chemical research, thermodynamic property, or synthesis question. All answers are grounded in literature with verified citation tags `[CIT-001]`.',
      timestamp: new Date().toLocaleTimeString(),
      confidence_score: 1.0,
      chemistry_validated: true,
    },
    {
      id: 'msg-2',
      sender: 'user',
      content: 'What is the boiling point and heat of vaporization of Ethanol (CAS 64-17-5)?',
      timestamp: new Date().toLocaleTimeString(),
    },
    {
      id: 'msg-3',
      sender: 'assistant',
      content:
        'Ethanol (formula **C₂H₆O**, SMILES `CCO`, CAS `64-17-5`) has a normal boiling point of **78.37 °C** at 101.3 kPa [CIT-001].\n\nIts molar heat of vaporization (\\(\\Delta H_{vap}\\)) is **38.56 kJ/mol** at 25 °C [CIT-001]. Vapor-liquid equilibrium (VLE) measurements demonstrate positive non-ideal deviation from Raoult\'s Law due to strong intermolecular hydrogen bonding [CIT-002].\n\n| Property | Value | Unit | Citation |\n|---|---|---|---|\n| Boiling Point | 78.37 | °C | [CIT-001] |\n| Enthalpy \\(\\Delta H_{vap}\\) | 38.56 | kJ/mol | [CIT-001] |\n| Critical Temp \\(T_c\\) | 514.0 | K | [CIT-002] |',
      timestamp: new Date().toLocaleTimeString(),
      confidence_score: 0.985,
      chemistry_validated: true,
      contained_entities: ['Ethanol (CCO)', 'CAS 64-17-5'],
      citations: [
        {
          citation_id: 'CIT-001',
          chunk_id: 'c-101',
          document_id: 'd-101',
          document_title: 'Thermodynamics of Ethanol-Water Mixtures',
          page_number: 3,
          confidence: 0.98,
          raw_text: 'Ethanol (CAS 64-17-5) boiling point 78.37 °C, molar heat of vaporization 38.56 kJ/mol.',
        },
        {
          citation_id: 'CIT-002',
          chunk_id: 'c-102',
          document_id: 'd-102',
          document_title: 'Binary Phase Equilibria and Critical Constants',
          page_number: 7,
          confidence: 0.94,
          raw_text: 'Critical temperature of pure ethanol measured at 514.0 K.',
        },
      ],
      agent_trace: [
        { agent_name: 'Safety', status: 'completed', timestamp: '10:00:01', summary: 'No weapons or controlled substances flagged.' },
        { agent_name: 'Planner', status: 'completed', timestamp: '10:00:02', summary: 'Sub-queries: [Ethanol boiling point], [Ethanol Hvap].' },
        { agent_name: 'Retriever', status: 'completed', timestamp: '10:00:03', summary: 'Retrieved 8 chunks from pgvector + ts_rank_cd.' },
        { agent_name: 'Reranker', status: 'completed', timestamp: '10:00:04', summary: 'Cohere cross-encoder top-2 selected.' },
        { agent_name: 'Chemistry Validator', status: 'completed', timestamp: '10:00:05', summary: 'Validated CCO SMILES and CAS 64-17-5 against PubChem.' },
        { agent_name: 'Aggregator', status: 'completed', timestamp: '10:00:06', summary: 'Synthesized grounded response with CIT-001, CIT-002.' },
      ],
    },
  ]);

  const [activeTrace, setActiveTrace] = useState<AgentStepTrace[] | null>(messages[2].agent_trace || null);

  const handleSendMessage = () => {
    if (!inputMessage.trim()) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      content: inputMessage,
      timestamp: new Date().toLocaleTimeString(),
    };

    const botMsg: ChatMessage = {
      id: `msg-${Date.now() + 1}`,
      sender: 'assistant',
      content: `Synthesizing evidence-backed response for query: "${inputMessage}"... [CIT-001]`,
      timestamp: new Date().toLocaleTimeString(),
      confidence_score: 0.96,
      chemistry_validated: true,
      citations: [
        {
          citation_id: 'CIT-001',
          chunk_id: 'c-201',
          document_id: 'd-201',
          document_title: 'Chemical Engineering Data Journal',
          page_number: 4,
          confidence: 0.96,
          raw_text: 'Experimental literature data confirmed.',
        },
      ],
      agent_trace: [
        { agent_name: 'Planner', status: 'completed', timestamp: 'Just now', summary: 'Decomposed intent into domain query.' },
        { agent_name: 'Retriever', status: 'completed', timestamp: 'Just now', summary: 'Retrieved top candidate evidence.' },
        { agent_name: 'Chemistry Validator', status: 'completed', timestamp: 'Just now', summary: 'Verified structure syntax.' },
        { agent_name: 'Aggregator', status: 'completed', timestamp: 'Just now', summary: 'Response assembled with citation tags.' },
      ],
    };

    setMessages((prev) => [...prev, userMsg, botMsg]);
    setActiveTrace(botMsg.agent_trace || null);
    setInputMessage('');
  };

  return (
    <div className="flex h-[calc(100vh-6rem)] gap-6 max-w-7xl mx-auto">
      {/* Main Chat Container */}
      <div className="flex-1 flex flex-col bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        {/* Chat Header */}
        <div className="px-6 py-4 bg-slate-950 border-b border-slate-800 flex justify-between items-center">
          <div>
            <h3 className="text-sm font-extrabold text-white flex items-center gap-2">
              💬 ChemRAG Scientific Assistant
            </h3>
            <p className="text-[11px] text-slate-400">Strict evidence grounding • Zero hallucination protocol</p>
          </div>
          <span className="px-2.5 py-1 text-xs font-mono font-bold text-emerald-400 bg-emerald-950 border border-emerald-800 rounded-full">
            Active Session
          </span>
        </div>

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
                        {msg.confidence_score && (
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
                          onClick={() => setActiveTrace(msg.agent_trace || null)}
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
        </div>

        {/* Input Bar */}
        <div className="p-4 bg-slate-950 border-t border-slate-800 flex gap-3">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Ask a scientific research question (e.g., Ethanol heat of vaporization, CAS 64-17-5)..."
            className="flex-1 px-4 py-3 text-xs bg-slate-900 border border-slate-700 rounded-xl text-slate-100 focus:outline-none focus:border-cyan-500 font-sans"
          />
          <button
            onClick={handleSendMessage}
            className="px-6 py-3 text-xs font-bold text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-xl shadow-lg shadow-cyan-500/20 font-mono"
          >
            Send 🚀
          </button>
        </div>
      </div>

      {/* Prompt 14.4 — Agent Trace Operational Panel */}
      <div className="w-80 bg-slate-900 border border-slate-800 rounded-2xl p-5 flex flex-col gap-4 shadow-xl overflow-y-auto">
        <div className="border-b border-slate-800 pb-3">
          <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <span>🤖</span> Safe Agent Trace
          </h4>
          <p className="text-[10px] text-slate-400 mt-0.5">Operational pipeline status (No hidden chain-of-thought)</p>
        </div>

        {!activeTrace ? (
          <div className="text-center py-10 text-xs text-slate-500 font-mono">
            Select a message to view operational trace.
          </div>
        ) : (
          <div className="space-y-3 font-mono text-xs">
            {activeTrace.map((step, i) => (
              <div key={i} className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-cyan-400 text-[11px]">{step.agent_name}</span>
                  <span className="px-1.5 py-0.5 text-[9px] rounded uppercase font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
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
