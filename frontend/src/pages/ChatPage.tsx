import { useState, type FormEvent } from 'react';
import { useMutation } from '@tanstack/react-query';
import { DataState } from '../components/DataState';
import { PageHeader } from '../components/PageHeader';
import { api } from '../lib/api';
import type { ChatResponse } from '../lib/types';

const exampleQuestions = [
  'Compare current plan prices',
  'What changed recently?',
  'What promotions does Verizon have?',
  "How has T-Mobile Essentials pricing changed?",
  "What are the eligibility requirements for Verizon's device promotion?",
  "How much does the Verizon plan cost and what conditions apply to its iPhone promotion?",
];

type Turn = { question: string; response: ChatResponse };

const TOOL_LABELS: Record<string, string> = {
  get_current_plan_prices: 'Current Plan Prices',
  get_plan_price_history: 'Plan Price History',
  get_device_price_history: 'Device Price History',
  get_promotions: 'Promotions',
  get_recent_changes: 'Recent Changes',
  search_competitor_documents: 'Competitor Documents',
};

export default function ChatPage() {
  const [message, setMessage] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const askMutation = useMutation({
    mutationFn: api.askAi,
    onSuccess: (response, question) => {
      setTurns((current) => [...current, { question, response }]);
      setMessage('');
    },
  });

  function submitQuestion(question: string) {
    const trimmed = question.trim();
    if (!trimmed || askMutation.isPending) return;
    askMutation.mutate(trimmed);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitQuestion(message);
  }

  return (
    <div className="dashboard-page chat-page">
      <PageHeader
        eyebrow="Ask AI"
        title="Competitive Intelligence Assistant"
        note="Answers use tracked competitive data only. No external market search is performed."
      />
      <section className="chat-shell panel" aria-label="Competitive intelligence chat">
        <div className="chat-intro">
          <span className="ai-status-pill">AI-generated from tracked data</span>
          <span className="synthetic-status-pill">Seeded/demo changes are labeled</span>
          <p>Ask about current or historical plan pricing, device prices, promotions, and recorded changes.</p>
        </div>

        <div className="suggested-questions">
          <span className="suggested-questions-label">Suggested questions</span>
          <div className="suggested-questions-list">
            {exampleQuestions.map((question) => (
              <button key={question} type="button" className="suggested-question-chip" onClick={() => submitQuestion(question)} disabled={askMutation.isPending}>
                {question}
              </button>
            ))}
          </div>
        </div>

        {turns.length === 0 ? (
          <div className="chat-empty-state">
            <strong>Start with a question</strong>
            <span>The assistant selects the right tools — pricing, history, promotions, or document search — before generating its answer.</span>
          </div>
        ) : (
          <div className="chat-transcript" aria-live="polite">
            {turns.map((turn, index) => (
              <div className="chat-turn" key={`${index}-${turn.question}`}>
                <div className="chat-message user-message"><span className="chat-avatar user-avatar">You</span><p>{turn.question}</p></div>
                <div className="chat-message assistant-message">
                  <span className="chat-avatar ai-avatar">AI</span>
                  <div className="assistant-content">
                    <div className="chat-answer-label">AI-generated · tracked competitive data · {turn.response.model}</div>
                    <p className="chat-answer">{turn.response.answer}</p>
                    {turn.response.data_scope.synthetic_change_records_included ? <div className="chat-demo-note">Contains synthetic seeded change records; these are not automatically detected events.</div> : null}
                    {turn.response.data_scope.document_sources_included ? <div className="chat-demo-note">Contains excerpts from synthetic demo competitor documents (promotion terms/eligibility), not live or scraped content.</div> : null}
                    {turn.response.data_scope.tools_used?.length ? (
                      <div className="chat-sources-plain">
                        <span className="chat-sources-plain-label">Sources</span>
                        <ul>{turn.response.data_scope.tools_used.map((tool) => (
                          <li key={tool}>{TOOL_LABELS[tool] ?? tool}</li>
                        ))}</ul>
                      </div>
                    ) : null}
                    {turn.response.sources.length ? (
                      <details className="chat-sources">
                        <summary>View detailed source records ({turn.response.sources.length})</summary>
                        <ul>{turn.response.sources.map((source) => (
                          <li key={source.source_id}>
                            <strong>{source.source_id}</strong> · {source.summary}
                            {source.record_origin === 'synthetic_seeded' || source.record_origin === 'synthetic_document' ? <span className="origin-badge synthetic-origin">Synthetic/demo</span> : null}
                          </li>
                        ))}</ul>
                      </details>
                    ) : <small className="chat-no-sources">No matching tracked records were available.</small>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {askMutation.isPending ? <DataState status="loading" message="Retrieving records and generating answer" detail="The assistant only receives deterministic context selected by the backend." /> : null}
        {askMutation.isError ? <DataState status="error" message="Assistant could not answer" detail={`${askMutation.error.message} Try again or narrow the question to tracked plans, devices, promotions, or changes.`} /> : null}

        <form className="chat-composer" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="chat-question">Ask about competitive data</label>
          <textarea
            id="chat-question"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Ask about plans, prices, devices, promotions, or changes…"
            rows={2}
            maxLength={1000}
            disabled={askMutation.isPending}
          />
          <div className="composer-footer">
            <small>{message.length}/1000 · Answers cite tracked source IDs</small>
            <button className="primary-button" type="submit" disabled={!message.trim() || askMutation.isPending}>
              {askMutation.isPending ? 'Thinking…' : 'Send question'}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
