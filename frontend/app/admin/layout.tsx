'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import { AdminShell } from '@/components/layout/AdminShell';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  // If on admin login page, don't wrap in AdminShell
  if (pathname === '/admin/login') {
    return <>{children}</>;
  }

  return <AdminShell>{children}</AdminShell>;
}
