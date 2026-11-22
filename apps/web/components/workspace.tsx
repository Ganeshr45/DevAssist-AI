'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Activity, BookOpen, ChevronDown, Command, LogOut, MessageSquare, Settings2, Shield, Sparkles } from 'lucide-react';
import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';

const primary=[{href:'/dashboard',label:'Assistant',icon:Sparkles},{href:'/knowledge',label:'Knowledge base',icon:BookOpen},{href:'/history',label:'Conversations',icon:MessageSquare}];
const managed=[{href:'/analytics',label:'Analytics',icon:Activity},{href:'/settings',label:'Settings',icon:Settings2}];

export function Workspace({children}:{children:ReactNode}) {
  const path=usePathname();const router=useRouter();const {user,ready,signOut}=useAuth();const [menuOpen,setMenuOpen]=useState(false);
  useEffect(()=>{if(ready&&!user)router.replace('/login')},[ready,user,router]);
  useEffect(()=>{function onKey(event:KeyboardEvent){if(event.key==='Escape')setMenuOpen(false)}window.addEventListener('keydown',onKey);return()=>window.removeEventListener('keydown',onKey)},[]);
  if(!ready||!user)return <main className="content" aria-live="polite">Loading your workspace…</main>;
  const navLink=({href,label,icon:Icon}:{href:string;label:string;icon:typeof Sparkles})=><Link key={href} href={href} onClick={()=>setMenuOpen(false)} className={`nav-link ${path===href?'active':''}`}><Icon size={15}/>{label}</Link>;
  return <div className="shell">
    <aside id="primary-navigation" className={`sidebar ${menuOpen?'mobile-open':''}`} aria-label="Main navigation">
      <div className="brand"><div className="brand-mark">D</div><span>DevAssist</span><span className="tag">BETA</span></div>
      <div className="nav-label">Workspace</div>{primary.map(navLink)}
      <div className="nav-label" style={{marginTop:20}}>Manage</div>{managed.map(navLink)}{user.is_admin&&navLink({href:'/admin',label:'Admin',icon:Shield})}
      <div className="spacer"/><Link className="nav-link" href="/settings" onClick={()=>setMenuOpen(false)}><Command size={15}/>Keyboard shortcuts <span className="tag">⌘ K</span></Link>
      <div className="profile"><div className="avatar">{user.display_name.slice(0,1).toUpperCase()}</div><div style={{minWidth:0}}><strong>{user.display_name}</strong><div className="profile-email">{user.email}</div></div><button aria-label="Sign out" onClick={async()=>{await signOut();router.replace('/login')}} className="logout-button"><LogOut size={15}/></button><ChevronDown size={13} className="profile-chevron"/></div>
    </aside>
    {menuOpen&&<button className="menu-backdrop" aria-label="Close navigation" onClick={()=>setMenuOpen(false)}/>}
    <main className="main"><header className="topbar"><span className="row"><button className="mobile-menu" aria-label="Open navigation" aria-expanded={menuOpen} aria-controls="primary-navigation" onClick={()=>setMenuOpen(value=>!value)}><Command size={15}/></button>Workspace <span style={{color:'#4c525b'}}> / </span> <span style={{color:'#e5e7e9'}}>{path.split('/')[1]?.replace(/^./,s=>s.toUpperCase())}</span></span><span className="row"><span className="tag">Private workspace</span></span></header>{children}</main>
  </div>
}
