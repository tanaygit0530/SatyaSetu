const configuredBotNumber = process.env.NEXT_PUBLIC_WHATSAPP_BOT_NUMBER || '+1 415 523 8886';
const cleanBotDigits = configuredBotNumber.replace(/\D/g, '');

export const APP_CONFIG = {
  name: 'SatyaSetu',
  tagline: "Before You Forward It, Verify It. Real-time truth verification in your language.",
  version: 'v4.2 LTS',
  compliance: 'IFCN Signatory Tier-1 Standard',
  repositoryId: '0x9AF...41B',
  // Official SatyaSetu WhatsApp Bot Tipline Service Number (NOT user personal number)
  whatsappNumber: configuredBotNumber,
  whatsappDeepLink: `https://wa.me/${cleanBotDigits}?text=SatyaSetu%20Forward`,
  logoUrl: 'https://lh3.googleusercontent.com/aida/AEtjO1V5nPBOWqp8I-AH02hP-0Soj3uU1ZbC8nr6bF1G7V0jSgl_gkM7IukfJ-oiXZ-yo3MeHnwS7PzIARrAh3Gemfpt4VgwXtS1OJRgNJJihEg7cTPGAmEXwsBgZaa59xR-MZcaHqdeZJlGoKhBdrWAy5mytpNpH6Oj9Sb-NXUR3AXq8tg2txCxPClFyfwcFkCUuDkVGXMTZGmR94LESNo_uxO5QjLhAmuf-_6K_wzH2yYR',
};

export const CITIZEN_NAV_LINKS = [
  { label: 'Dashboard', path: '/dashboard', icon: 'dashboard' },
  { label: 'Check Claim', path: '/check', icon: 'fact_check' },
  { label: 'History', path: '/history', icon: 'history' },
  { label: 'WhatsApp', path: '/whatsapp', icon: 'chat' },
  { label: 'How We Decide', path: '/how-we-decide', icon: 'policy' },
];

export const ADMIN_NAV_LINKS = [
  { label: 'Desk Overview', path: '/admin', icon: 'dashboard' },
  { label: 'Live Checks', path: '/admin/checks', icon: 'fact_check' },
  { label: 'Rumour Memory', path: '/admin/rumours', icon: 'fingerprint' },
  { label: 'Review Queue', path: '/admin/review', icon: 'rate_review', badge: '14' },
  { label: 'Sources Registry', path: '/admin/sources', icon: 'policy' },
];
