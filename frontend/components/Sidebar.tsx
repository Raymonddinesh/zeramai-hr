"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const NAV = [
  { href: "/dashboard",    label: "Dashboard",    icon: "🏠", roles: ["super_admin","hr_admin","hiring_manager","finance","employee"] },
  { href: "/candidates",   label: "Candidates",   icon: "👤", roles: ["super_admin","hr_admin","hiring_manager"] },
  { href: "/documents",    label: "Documents",    icon: "📄", roles: ["super_admin","hr_admin","employee"] },
  { href: "/attendance",   label: "Attendance",   icon: "📅", roles: ["super_admin","hr_admin","employee"] },
  { href: "/leave",        label: "Leave",        icon: "🏖️", roles: ["super_admin","hr_admin","employee"] },
  { href: "/evaluations",  label: "Evaluations",  icon: "⭐", roles: ["super_admin","hr_admin","hiring_manager","employee"] },
  { href: "/stipends",     label: "Stipends",     icon: "💰", roles: ["super_admin","hr_admin","finance","employee"] },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  const visibleLinks = NAV.filter((n) => user && n.roles.includes(user.role));

  return (
    <aside className="w-56 min-h-screen bg-indigo-900 text-white flex flex-col">
      <div className="px-5 py-5 border-b border-indigo-700">
        <h1 className="text-lg font-bold tracking-tight">Zeramai HR</h1>
        <p className="text-xs text-indigo-300 mt-1 truncate">{user?.email}</p>
        <span className="text-xs bg-indigo-700 rounded px-2 py-0.5 mt-1 inline-block capitalize">
          {user?.role.replace("_", " ")}
        </span>
      </div>
      <nav className="flex-1 py-4 space-y-1 px-2">
        {visibleLinks.map((n) => {
          const active = pathname.startsWith(n.href);
          return (
            <Link
              key={n.href}
              href={n.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
                active
                  ? "bg-indigo-600 text-white"
                  : "text-indigo-200 hover:bg-indigo-800 hover:text-white"
              }`}
            >
              <span>{n.icon}</span>
              {n.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-indigo-700">
        <button
          onClick={logout}
          className="w-full text-sm text-indigo-300 hover:text-white transition text-left"
        >
          Sign out →
        </button>
      </div>
    </aside>
  );
}
