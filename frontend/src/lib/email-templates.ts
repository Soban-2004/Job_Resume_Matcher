import type { CandidateResult } from "@/lib/types";

export interface EmailTemplate {
  id: string;
  label: string;
  subject: (c: CandidateResult, jobRole: string) => string;
  body: (c: CandidateResult, jobRole: string) => string;
}

function firstName(c: CandidateResult): string {
  const name = c.candidate_name?.trim();
  return name ? name.split(/\s+/)[0] : "there";
}

export const EMAIL_TEMPLATES: EmailTemplate[] = [
  {
    id: "interview_invite",
    label: "Interview Invitation",
    subject: (c, jobRole) => `Interview invitation -- ${jobRole}`,
    body: (c, jobRole) =>
      `Hi ${firstName(c)},\n\n` +
      `Thanks for applying for the ${jobRole} role. We'd like to invite you to an interview to discuss your background further.\n\n` +
      `Could you share a few times that work for you over the next week?\n\n` +
      `Best regards,\nRecruiting Team`,
  },
  {
    id: "technical_round",
    label: "Technical Round",
    subject: (c, jobRole) => `Next step: Technical round -- ${jobRole}`,
    body: (c, jobRole) =>
      `Hi ${firstName(c)},\n\n` +
      `Following your initial interview for the ${jobRole} role, we'd like to move forward with a technical round.\n\n` +
      `This will cover the core skills relevant to the position. Please let us know your availability.\n\n` +
      `Best regards,\nRecruiting Team`,
  },
  {
    id: "hr_round",
    label: "HR Round",
    subject: (c, jobRole) => `Next step: HR round -- ${jobRole}`,
    body: (c, jobRole) =>
      `Hi ${firstName(c)},\n\n` +
      `Great news -- you've cleared the technical evaluation for the ${jobRole} role. We'd like to schedule an HR round next.\n\n` +
      `Please share your availability for a short call this week.\n\n` +
      `Best regards,\nRecruiting Team`,
  },
  {
    id: "request_documents",
    label: "Request Documents",
    subject: () => `Documents needed for your application`,
    body: (c, jobRole) =>
      `Hi ${firstName(c)},\n\n` +
      `As we move forward with your application for the ${jobRole} role, could you please send over your updated resume, ` +
      `references, and any relevant certificates?\n\n` +
      `Best regards,\nRecruiting Team`,
  },
  {
    id: "rejection",
    label: "Rejection",
    subject: (c, jobRole) => `Update on your application -- ${jobRole}`,
    body: (c, jobRole) =>
      `Hi ${firstName(c)},\n\n` +
      `Thank you for taking the time to apply for the ${jobRole} role. After careful review, we've decided to move forward ` +
      `with other candidates whose experience more closely matches this position.\n\n` +
      `We appreciate your interest and encourage you to apply for future openings.\n\n` +
      `Best regards,\nRecruiting Team`,
  },
];
