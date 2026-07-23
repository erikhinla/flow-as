export const LAYER_ORDER = [
  "Context",
  "System Architecture",
  "Activation",
  "Interface"
];

export const ARVA_INTRO =
  "I'm going to ask a few questions to find where the system is losing clarity. A gap is a signal.";

export const questions = [
  {
    layer: "Context",
    prompt:
      "Do you have one place where your business logic, offer structure, and positioning are documented and consistently referenced?",
    options: [
      ["stable", "Yes: documented, current, and used"],
      ["watch", "Partially: exists but is outdated or inconsistently used"],
      ["gap", "No: it exists in my head or scattered notes"],
      ["gap", "No: I have not built this yet"]
    ]
  },
  {
    layer: "Context",
    prompt:
      "When you describe what you do, is the language consistent across website, sales calls, emails, and onboarding?",
    options: [
      ["stable", "Yes: consistent across all surfaces"],
      ["watch", "Mostly: minor inconsistencies"],
      ["gap", "No: it shifts depending on context or who is communicating"]
    ]
  },
  {
    layer: "Context",
    prompt:
      "When a new opportunity or problem appears, do you have a defined framework for deciding what to pursue?",
    options: [
      ["stable", "Yes: documented decision process"],
      ["watch", "Informally: mental rules but nothing written"],
      ["gap", "No: decisions happen case by case"]
    ]
  },
  {
    layer: "System Architecture",
    prompt:
      "Are your core workflows documented and repeatable: intake, delivery, follow-up, and reporting?",
    options: [
      ["stable", "Yes: documented, followed, and updated"],
      ["watch", "Partially: some workflows are documented"],
      ["gap", "No: workflows exist in practice but are not written down"],
      ["gap", "No: workflows are inconsistent or underdefined"]
    ]
  },
  {
    layer: "System Architecture",
    prompt:
      "When a client moves through your system, is the path from first contact to delivered outcome clearly defined?",
    options: [
      ["stable", "Yes: every step is defined and owned"],
      ["watch", "Partially: the path exists but has gaps"],
      ["gap", "No: the path is unclear or varies significantly"]
    ]
  },
  {
    layer: "System Architecture",
    prompt:
      "Are your tools configured for your workflows, or are they mostly defaults with manual workarounds?",
    options: [
      ["stable", "Configured: tools match our workflows"],
      ["watch", "Partially configured: some custom, some default"],
      ["gap", "Default: significant manual work"],
      ["gap", "Inconsistent: different people use tools differently"]
    ]
  },
  {
    layer: "System Architecture",
    prompt: "What percentage of your repeatable operational tasks are automated?",
    options: [
      ["stable", "More than 60%"],
      ["watch", "30 to 60%"],
      ["gap", "Less than 30%"],
      ["gap", "Essentially none"]
    ]
  },
  {
    layer: "Activation",
    prompt: "Do you have a defined and functioning system for capturing leads?",
    options: [
      ["stable", "Yes: functional, tested, producing leads"],
      ["watch", "Partially: exists but not consistently used or optimized"],
      ["gap", "No: leads come in ad hoc"]
    ]
  },
  {
    layer: "Activation",
    prompt: "Is your follow-up process documented and executed consistently?",
    options: [
      ["stable", "Yes: automated or consistently manual with defined steps"],
      ["watch", "Partially: follow-up varies by rep or situation"],
      ["gap", "No: follow-up is reactive and inconsistent"]
    ]
  },
  {
    layer: "Activation",
    prompt:
      "Do you have a defined system for producing and distributing content or outreach?",
    options: [
      ["stable", "Yes: calendar, workflow, and distribution system exist"],
      ["watch", "Partially: content happens but without a consistent system"],
      ["gap", "No: content happens when time allows"]
    ]
  },
  {
    layer: "Interface",
    prompt:
      "Does your website, onboarding, and sales material accurately reflect how your system actually works?",
    options: [
      ["stable", "Yes: fully aligned"],
      ["watch", "Mostly: minor gaps"],
      ["gap", "No: significant gaps between expectation and delivery"]
    ]
  },
  {
    layer: "Interface",
    prompt:
      "When a new client enters your system, is the experience consistent and governed by a defined process?",
    options: [
      ["stable", "Yes: consistent, documented, and tested"],
      ["watch", "Partially: process exists but varies"],
      ["gap", "No: intake is handled ad hoc"]
    ]
  },
  {
    layer: "Operational Context",
    prompt: "In plain language, describe your biggest operational friction right now.",
    text: true,
    placeholder:
      "Example: leads come from multiple places and I don't have one reliable follow-up path..."
  },
  {
    layer: "Operational Context",
    prompt: "What one thing, if resolved, would most change how your business operates?",
    text: true,
    placeholder:
      "Example: one clear source of context for offers, intake, and client status..."
  },
  {
    layer: "Operational Context",
    prompt: "Have you tried to solve this before? If yes, what stopped it from working?",
    text: true,
    placeholder:
      "Optional, but useful: tool complexity, time, unclear ownership, bad setup..."
  }
];

export { buildSpeechPrompt, layerBeatForIndex } from "./arva-conversation-hints.js";
