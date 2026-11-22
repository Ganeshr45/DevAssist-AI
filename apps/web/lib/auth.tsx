'use client';
import { createContext, useContext, useEffect, useMemo, useState } from 'react';

type User = { id: string; email: string; display_name: string; is_admin: boolean };
type AuthContextValue = { user: User | null; accessToken: string | null; ready: boolean; setSession: (token: string, user: User) => void; signOut: () => Promise<void>; apiFetch: (path: string, init?: RequestInit) => Promise<Response> };
const AuthContext = createContext<AuthContextValue | null>(null);
const api = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

export function AuthProvider({children}:{children:React.ReactNode}) {
  const [user,setUser]=useState<User|null>(null); const [accessToken,setAccessToken]=useState<string|null>(null); const [ready,setReady]=useState(false);
  useEffect(()=>{let mounted=true; fetch(`${api}/auth/refresh`,{method:'POST',credentials:'include'}).then(async r=>{if(r.ok){const data=await r.json();if(mounted){setUser(data.user);setAccessToken(data.access_token)}}}).catch(()=>{}).finally(()=>{if(mounted)setReady(true)});return()=>{mounted=false}},[]);
  const value=useMemo<AuthContextValue>(()=>({user,accessToken,ready,setSession:(token,nextUser)=>{setAccessToken(token);setUser(nextUser)},signOut:async()=>{await fetch(`${api}/auth/logout`,{method:'POST',credentials:'include'}).catch(()=>{});setAccessToken(null);setUser(null)},apiFetch:async(path,init={})=>{let token=accessToken;const send=(current:string|null)=>{const headers=new Headers(init.headers);if(current)headers.set('Authorization',`Bearer ${current}`);if(init.body!==undefined&&!(init.body instanceof FormData))headers.set('Content-Type','application/json');return fetch(`${api}${path}`,{...init,headers,credentials:'include'})};let response=await send(token);if(response.status===401){const refreshed=await fetch(`${api}/auth/refresh`,{method:'POST',credentials:'include'});if(refreshed.ok){const next=await refreshed.json();token=next.access_token;setAccessToken(next.access_token);setUser(next.user);response=await send(token)}}return response}}),[user,accessToken,ready]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth(){const value=useContext(AuthContext);if(!value)throw new Error('useAuth must be used inside AuthProvider');return value}
export const API_URL=api;
