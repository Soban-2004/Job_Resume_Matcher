"use client";

import { useState } from "react";
import { Mail, Send, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { EMAIL_TEMPLATES } from "@/lib/email-templates";
import { sendCandidateEmail } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { CandidateResult } from "@/lib/types";

type SendState = "idle" | "sending" | "sent" | "error";

export function EmailComposer({ candidate, jobRole }: { candidate: CandidateResult; jobRole: string }) {
  const [open, setOpen] = useState(false);
  const [templateId, setTemplateId] = useState(EMAIL_TEMPLATES[0].id);
  const [toEmail, setToEmail] = useState(candidate.candidate_email ?? "");
  const [subject, setSubject] = useState(EMAIL_TEMPLATES[0].subject(candidate, jobRole));
  const [body, setBody] = useState(EMAIL_TEMPLATES[0].body(candidate, jobRole));
  const [state, setState] = useState<SendState>("idle");
  const [error, setError] = useState<string | null>(null);

  function applyTemplate(id: string) {
    const template = EMAIL_TEMPLATES.find((t) => t.id === id) ?? EMAIL_TEMPLATES[0];
    setTemplateId(template.id);
    setSubject(template.subject(candidate, jobRole));
    setBody(template.body(candidate, jobRole));
  }

  async function handleSend() {
    setState("sending");
    setError(null);
    try {
      await sendCandidateEmail(toEmail, subject, body);
      setState("sent");
    } catch (e) {
      setState("error");
      setError(e instanceof Error ? e.message : "Failed to send email.");
    }
  }

  if (!open) {
    return (
      <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setOpen(true)}>
        <Mail className="size-3.5" />
        Send Email
      </Button>
    );
  }

  return (
    <Card className="flex flex-col gap-4 p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-foreground">Send Email</h3>
        <Button variant="ghost" size="icon-sm" onClick={() => setOpen(false)}>
          <X className="size-3.5" />
        </Button>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {EMAIL_TEMPLATES.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => applyTemplate(t.id)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              t.id === templateId
                ? "border-primary/40 bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email-to">To</Label>
        <Input
          id="email-to"
          type="email"
          value={toEmail}
          onChange={(e) => setToEmail(e.target.value)}
          placeholder="candidate@example.com"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email-subject">Subject</Label>
        <Input id="email-subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email-body">Message</Label>
        <Textarea id="email-body" rows={8} value={body} onChange={(e) => setBody(e.target.value)} />
      </div>

      <div className="flex items-center gap-3">
        <Button
          size="sm"
          className="gap-1.5"
          disabled={!toEmail || state === "sending"}
          onClick={handleSend}
        >
          <Send className="size-3.5" />
          {state === "sending" ? "Sending..." : "Send"}
        </Button>
        {state === "sent" && <span className="text-sm text-emerald-600 dark:text-emerald-400">Sent.</span>}
        {state === "error" && <span className="text-sm text-red-600 dark:text-red-400">{error}</span>}
      </div>
    </Card>
  );
}
