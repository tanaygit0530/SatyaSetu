import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Verdict } from '@/types';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getVerdictConfig(verdict: Verdict) {
  switch (verdict) {
    case 'VERIFIED':
      return {
        label: 'Verified',
        hindiLabel: 'सत्यापित (सत्य)',
        marathiLabel: 'पडताळणीकृत (सत्य)',
        icon: 'verified',
        colorClass: 'text-[#146336]',
        bgClass: 'bg-[#EAF6EE]',
        borderClass: 'border-[#B8E4C8]',
        badgeClass: 'bg-[#EAF6EE] text-[#146336] border-[#B8E4C8]',
        bannerBg: 'bg-emerald-50 border-emerald-200',
        dotColor: 'bg-[#1E8E4E]',
        description: 'Strongly corroborated by official public records.',
      };
    case 'FALSE':
      return {
        label: 'False',
        hindiLabel: 'असत्य (झूठ)',
        marathiLabel: 'खोटे (असत्य)',
        icon: 'cancel',
        colorClass: 'text-[#991B1B]',
        bgClass: 'bg-[#FDF2F2]',
        borderClass: 'border-[#F6B8B8]',
        badgeClass: 'bg-[#FDF2F2] text-[#991B1B] border-[#F6B8B8]',
        bannerBg: 'bg-red-50 border-red-200',
        dotColor: 'bg-[#C62F2F]',
        description: 'Fabricated claim directly refuted by primary evidence.',
      };
    case 'OUTDATED':
      return {
        label: 'Outdated',
        hindiLabel: 'पुराना / अप्रासंगिक',
        marathiLabel: 'कालबाह्य / जुने',
        icon: 'update',
        colorClass: 'text-[#A04F05]',
        bgClass: 'bg-[#FEF7ED]',
        borderClass: 'border-[#FCD4A5]',
        badgeClass: 'bg-[#FEF7ED] text-[#A04F05] border-[#FCD4A5]',
        bannerBg: 'bg-amber-50 border-amber-200',
        dotColor: 'bg-[#D9730D]',
        description: 'Previously authentic notice recirculated out of chronological context.',
      };
    case 'PARTLY_SUPPORTED':
      return {
        label: 'Partly Supported',
        hindiLabel: 'आंशिक रूप से सही',
        marathiLabel: 'अंशतः सत्य',
        icon: 'contrast',
        colorClass: 'text-[#856807]',
        bgClass: 'bg-[#FEFCE8]',
        borderClass: 'border-[#FBE89B]',
        badgeClass: 'bg-[#FEFCE8] text-[#856807] border-[#FBE89B]',
        bannerBg: 'bg-yellow-50 border-yellow-200',
        dotColor: 'bg-[#B7950B]',
        description: 'Contains factual elements combined with unverified or exaggerated details.',
      };
    case 'CANNOT_BE_CONFIRMED':
    default:
      return {
        label: 'Cannot Be Confirmed',
        hindiLabel: 'पुष्टि नहीं की जा सकी',
        marathiLabel: 'पुष्टी करता आली नाही',
        icon: 'help',
        colorClass: 'text-[#475569]',
        bgClass: 'bg-[#F1F5F9]',
        borderClass: 'border-[#CBD5E1]',
        badgeClass: 'bg-[#F1F5F9] text-[#475569] border-[#CBD5E1]',
        bannerBg: 'bg-slate-50 border-slate-200',
        dotColor: 'bg-[#64748B]',
        description: 'Inconclusive proof or subjective claims lacking official documentary trail.',
      };
  }
}

export function formatDate(dateString: string): string {
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateString;
  }
}
