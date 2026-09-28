"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

interface NavItem {
  href: string;
  label: string;
  icon: string;
  roles: string[];
}

const NAV_SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: "Core Platform",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: "🏠", roles: ["super_admin", "hr_admin", "hiring_manager", "finance", "employee"] },
      { href: "/organization", label: "Organization", icon: "🌐", roles: ["super_admin", "hr_admin"] },
      { href: "/documents", label: "Documents", icon: "📄", roles: ["super_admin", "hr_admin", "employee"] },
    ],
  },
  {
    title: "Workforce & Time",
    items: [
      { href: "/onboarding", label: "Onboarding", icon: "📋", roles: ["super_admin", "hr_admin", "employee"] },
      { href: "/attendance", label: "Attendance", icon: "📅", roles: ["super_admin", "hr_admin", "employee"] },
      { href: "/shifts", label: "Shift Rostering", icon: "⏰", roles: ["super_admin", "hr_admin", "employee"] },
      { href: "/leave", label: "Leave Engine", icon: "🏖️", roles: ["super_admin", "hr_admin", "employee"] },
    ],
  },
  {
    title: "Talent & Growth",
    items: [
      { href: "/jobs", label: "ATS & Requisitions", icon: "💼", roles: ["super_admin", "hr_admin", "hiring_manager"] },
      { href: "/candidates", label: "Candidates", icon: "👤", roles: ["super_admin", "hr_admin", "hiring_manager"] },
      { href: "/performance", label: "Performance & OKRs", icon: "🎯", roles: ["super_admin", "hr_admin", "hiring_manager", "employee"] },
      { href: "/engagement", label: "Engagement & Culture", icon: "❤️", roles: ["super_admin", "hr_admin", "hiring_manager", "employee"] },
      { href: "/learning", label: "Learning & Career", icon: "🎓", roles: ["super_admin", "hr_admin", "employee"] },
      { href: "/workforce-planning", label: "Workforce Planning & Org", icon: "🗺️", roles: ["super_admin", "hr_admin"] },
    ],
  },
  {
    title: "Communications & Knowledge",
    items: [
      { href: "/communications", label: "Communications Center", icon: "📢", roles: ["super_admin", "hr_admin", "hiring_manager", "employee", "finance"] },
      { href: "/knowledge", label: "Knowledge Hub", icon: "📚", roles: ["super_admin", "hr_admin", "hiring_manager", "employee", "finance"] },
      { href: "/communications/team", label: "Team Comms", icon: "👥", roles: ["super_admin", "hr_admin", "hiring_manager"] },
      { href: "/admin/communications", label: "Comms Admin", icon: "📡", roles: ["super_admin", "hr_admin"] },
      { href: "/admin/knowledge", label: "Knowledge Admin", icon: "📖", roles: ["super_admin", "hr_admin"] },
    ],
  },
  {
    title: "Finance & Analytics",
    items: [
      { href: "/payroll", label: "Payroll Engine", icon: "💵", roles: ["super_admin", "hr_admin", "finance"] },
      { href: "/global-payroll", label: "Global Payroll Hub", icon: "🌐", roles: ["super_admin", "hr_admin", "finance", "employee"] },
      { href: "/admin/global-payroll", label: "Global Payroll Admin", icon: "🗺️", roles: ["super_admin", "hr_admin", "finance"] },
      { href: "/finance", label: "Finance & Cost Center", icon: "🏛️", roles: ["super_admin", "hr_admin", "finance"] },
      { href: "/stipends", label: "Stipends", icon: "💰", roles: ["super_admin", "hr_admin", "finance", "employee"] },
      { href: "/analytics", label: "People Analytics", icon: "📊", roles: ["super_admin", "hr_admin", "finance"] },
    ],
  },
  {
    title: "Governance & IAM",
    items: [
      { href: "/compliance", label: "Compliance & Whistleblower", icon: "⚖️", roles: ["super_admin", "hr_admin", "employee"] },
      { href: "/governance", label: "Data Governance & Privacy", icon: "🛡️", roles: ["super_admin", "hr_admin"] },
      { href: "/settings", label: "Security, IAM & AI Suite", icon: "⚙️", roles: ["super_admin", "hr_admin"] },
    ],
  },
   
   {
       title: "Company Setup",
       items: [
           { href: "/legal-profile", label: "Company Legal Profile", icon: "🏢", roles: ["super_admin","hr_admin"] },
       ],
   },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  return (
    <aside className="w-64 min-h-screen bg-slate-900 text-white flex flex-col border-r border-slate-800 shrink-0">
      <div className="px-5 py-5 border-b border-slate-800">
        <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
          <span className="text-indigo-400">⚡</span> Zeramai HRMS
        </h1>
        <p className="text-[11px] text-slate-400 mt-1 truncate">{user?.email}</p>
        <span className="text-[10px] bg-indigo-950 text-indigo-300 border border-indigo-800 font-semibold rounded px-2 py-0.5 mt-1.5 inline-block uppercase tracking-wider">
          {user?.role?.replace("_", " ")}
        </span>
      </div>

      <nav className="flex-1 py-3 px-3 space-y-4 overflow-y-auto">
        {NAV_SECTIONS.map((section) => {
          const visibleItems = section.items.filter(
            (item) => user && item.roles.includes(user.role)
          );
          if (visibleItems.length === 0) return null;

          return (
            <div key={section.title} className="space-y-1">
              <p className="px-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                {section.title}
              </p>
              {visibleItems.map((n) => {
                const active = pathname.startsWith(n.href);
                return (
                  <Link
                    key={n.href}
                    href={n.href}
                    className={`flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                      active
                        ? "bg-indigo-600 text-white font-semibold shadow-sm"
                        : "text-slate-300 hover:bg-slate-800 hover:text-white"
                    }`}
                  >
                    <span className="text-sm">{n.icon}</span>
                    <span className="truncate">{n.label}</span>
                  </Link>
                );
              })}
            </div>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800">
        <button
          onClick={logout}
          className="w-full text-xs text-slate-400 hover:text-white transition flex items-center justify-between"
        >
          <span>Sign out of session</span>
          <span>→</span>
        </button>
      </div>
    </aside>
  );
}
