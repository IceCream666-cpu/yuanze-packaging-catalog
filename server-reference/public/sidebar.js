import {t,onLanguageChange} from './i18n.js';
// One sidebar controller shared by the employee and administrator workspaces.
const sidebar=document.querySelector('#sidebar');
const toggle=document.querySelector('#menuButton');
const backdrop=document.querySelector('.sidebar-backdrop');
const mobile=window.matchMedia?.('(max-width: 650px)');
const preferenceKey='yuanze.sidebar.collapsed';
let collapsed=false, mobileOpen=false;
try{collapsed=localStorage.getItem(preferenceKey)==='true';}catch{}

function syncSidebar(){
  if(!sidebar||!toggle)return;
  const isMobile=Boolean(mobile?.matches),visible=isMobile?mobileOpen:!collapsed;
  // Move focus before making the current focus container inert.
  if(!visible&&sidebar.contains(document.activeElement))toggle.focus({preventScroll:true});
  document.body.classList.toggle('sidebar-collapsed',!isMobile&&collapsed);
  document.body.classList.toggle('menu-open',isMobile&&mobileOpen);
  sidebar.inert=!visible;
  sidebar.setAttribute('aria-hidden',String(!visible));
  toggle.setAttribute('aria-expanded',String(visible));
  const label=t(visible?'收起侧栏':'显示侧栏');
  toggle.setAttribute('aria-label',label);
  toggle.title=label;
  const text=toggle.querySelector('.sidebar-toggle-label');
  if(text)text.textContent=label;
  if(backdrop)backdrop.hidden=!(isMobile&&mobileOpen);
}

export function closeMobileSidebar(){
  if(!mobile?.matches)return;
  mobileOpen=false;
  syncSidebar();
}

function setDesktopCollapsed(value){
  collapsed=value;
  try{localStorage.setItem(preferenceKey,String(value));}catch{}
}

toggle?.addEventListener('click',()=>{
  if(mobile?.matches)mobileOpen=!mobileOpen;
  else setDesktopCollapsed(!collapsed);
  syncSidebar();
  if(mobile?.matches&&mobileOpen)sidebar.querySelector('[data-sidebar-close]')?.focus({preventScroll:true});
});
document.querySelectorAll('[data-sidebar-close]').forEach(button=>button.addEventListener('click',()=>{
  if(mobile?.matches)mobileOpen=false;
  else setDesktopCollapsed(true);
  syncSidebar();
}));
document.addEventListener('keydown',event=>{
  if(event.key==='Escape'&&mobileOpen){event.preventDefault();closeMobileSidebar();}
});
mobile?.addEventListener?.('change',()=>{mobileOpen=false;syncSidebar();});
syncSidebar();

onLanguageChange(syncSidebar);
