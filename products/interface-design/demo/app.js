/* Frontend-only educational state. No persistence or external requests. */
const seed = [
  {id:104,title:'Подготовить зал для встречи',author:'Марина Соколова',initials:'МС',status:'new',created:'Сегодня, 10:40',body:'В среду собираем команду на встречу. Нужны свободный зал на шесть человек, экран и вода. Пожалуйста, назначьте ответственного за подготовку.',category:'Рабочее пространство'},
  {id:103,title:'Проверить макет страницы',author:'Илья Воронов',initials:'ИВ',status:'new',created:'Сегодня, 09:15',body:'Нужно проверить основной сценарий новой страницы и собрать замечания перед обсуждением с командой.',category:'Сайт и материалы'},
  {id:102,title:'Настроить доступ к проекту',author:'Елена Волкова',initials:'ЕВ',status:'new',created:'Вчера, 16:20',body:'Новому участнику команды нужен доступ к учебному проекту. Уточните необходимую роль и назначьте ответственного.',category:'Команда'},
  {id:101,title:'Обновить каталог материалов',author:'Андрей Морозов',initials:'АМ',status:'active',assignee:'Ирина Алексеева',due:'2026-10-28',created:'Вчера, 14:10',body:'В каталоге появились новые материалы. Нужно проверить названия и убрать устаревшие версии из основного списка.',category:'Сайт и материалы'}
];
const people=['Ирина Алексеева','Дмитрий Лебедев','Анна Петрова'];
let requests=structuredClone(seed),state={filter:'new',q:'',selected:104,step:'details',drafts:{},errors:{},error:'',saving:false,failNext:false};
const $=s=>document.querySelector(s),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const item=()=>requests.find(r=>r.id===state.selected);
const visibleRequests=()=>requests.filter(r=>(state.filter==='all'||r.status===state.filter)&&`${r.id} ${r.title} ${r.author}`.toLocaleLowerCase('ru').includes(state.q.toLocaleLowerCase('ru')));
function reconcileSelection(){const rows=visibleRequests();if(rows.some(r=>r.id===state.selected))return false;state.selected=rows[0]?.id??null;state.step='details';state.errors={};state.error='';return true;}
const draft=()=>state.drafts[state.selected]??(state.drafts[state.selected]={assignee:'',due:'2026-10-26',note:''});
const fmt=d=>new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'long'}).format(new Date(d+'T12:00:00'));
function readURL(){const p=new URL(location.href).searchParams;state.filter=['new','active','all'].includes(p.get('view'))?p.get('view'):'new';state.q=p.get('q')??'';state.selected=requests.some(r=>r.id===Number(p.get('request')))?Number(p.get('request')):104;state.step=p.get('step')==='assign'?'assign':'details';state.errors={};state.error='';}
function writeURL(replace=false){const url=new URL(location.href);url.search='';url.searchParams.set('view',state.filter);if(state.selected!==null)url.searchParams.set('request',state.selected);if(state.q)url.searchParams.set('q',state.q);if(state.step==='assign')url.searchParams.set('step','assign');history[replace?'replaceState':'pushState']({},'',url);}
function focusPanel(){requestAnimationFrame(()=>{const h=$('#detail h2');if(h){h.tabIndex=-1;h.focus({preventScroll:true});if(matchMedia('(max-width:720px)').matches)h.scrollIntoView({block:'start'});}});}
function renderQueue(){
 $('#filters').innerHTML=[['new','Новые'],['active','В работе'],['all','Все']].map(([v,label])=>`<button class="filter" data-action="filter" data-value="${v}" aria-pressed="${state.filter===v}">${label}<span>${v==='all'?requests.length:requests.filter(r=>r.status===v).length}</span></button>`).join('');
 const list=visibleRequests();
 $('#queue-count').textContent=`Показано ${list.length}`;
 $('#list').innerHTML=list.length?`<div class="table-wrap"><table><thead><tr><th scope="col">Заявка</th><th scope="col" class="author-column">Автор</th><th scope="col">Статус</th></tr></thead><tbody>${list.map(r=>`<tr class="${r.id===state.selected?'selected':''}"><td><button class="request-open" data-action="open" data-value="${r.id}" ${r.id===state.selected?'aria-current="true"':''}>${esc(r.title)}<small>№ ${r.id} / ${esc(r.created)}</small></button></td><td class="author-column author">${esc(r.author.split(' ')[0])}<br>${esc(r.author.split(' ')[1])}</td><td><span class="status ${r.status}">${r.status==='new'?'Новая':'В работе'}</span></td></tr>`).join('')}</tbody></table></div>`:`<div class="empty"><h3>${state.q?'Ничего не найдено':'Новых заявок пока нет'}</h3><p>${state.q?'Попробуйте другой запрос или сбросьте поиск.':'Назначенные заявки доступны в разделе «В работе».'}</p></div>`;
 $('#clear-search').hidden=!state.q;
}
function fieldError(name){return state.errors[name]?`<p class="field-error" id="${name}-error">${esc(state.errors[name])}</p>`:'';}
function renderDetail(){
 const r=item();if(!r){$('#detail').innerHTML='<div class="empty"><h2>Выберите заявку из списка</h2><p>Если список пуст, измените фильтр или поисковый запрос.</p></div>';return;}
 if(state.step==='success'){
  $('#detail').innerHTML=`<div class="detail-top"><span>Заявка № ${r.id}</span><span class="status active">В работе</span></div><h2 class="success-title">Назначение сохранено</h2><p class="success-line">${esc(r.title)}</p><dl class="meta"><dt>Исполнитель</dt><dd>${esc(r.assignee)}</dd><dt>Срок</dt><dd>${fmt(r.due)}</dd><dt>Комментарий</dt><dd>${esc(r.note||'Без комментария')}</dd></dl><div class="next-actions"><button class="primary" data-action="active-list">Открыть список в работе</button><button class="text-button" data-action="new-list">Вернуться к новым заявкам</button></div><p class="quiet">Это учебное назначение. Уведомление исполнителю не отправлялось.</p>`;return;
 }
 if(state.step==='assign'){
  const d=draft();
  $('#detail').innerHTML=`<button class="text-button back" data-action="back">Назад к заявке</button><h2>Назначить исполнителя</h2><p class="form-intro">${esc(r.title)}</p>${state.error?`<div class="error-banner" role="alert">${esc(state.error)}</div>`:''}<form id="assignment" novalidate aria-busy="${state.saving}"><div class="field"><label for="assignee">Кто возьмёт заявку</label><select id="assignee" name="assignee" ${state.saving?'disabled':''} ${state.errors.assignee?'aria-invalid="true" aria-describedby="assignee-error"':''}><option value="">Выберите исполнителя</option>${people.map(p=>`<option ${d.assignee===p?'selected':''}>${esc(p)}</option>`).join('')}</select>${fieldError('assignee')}</div><div class="field"><label for="due">К какому дню</label><input id="due" name="due" type="date" min="2026-10-25" value="${esc(d.due)}" ${state.saving?'disabled':''} ${state.errors.due?'aria-invalid="true" aria-describedby="due-error"':''}>${fieldError('due')}</div><div class="field"><label for="note">Комментарий исполнителю <span class="hint">(необязательно)</span></label><textarea id="note" name="note" maxlength="300" ${state.saving?'disabled':''}>${esc(d.note)}</textarea><p class="hint">Добавьте детали, которые помогут начать работу.</p></div><div class="form-actions"><button class="primary" type="submit" ${state.saving?'disabled':''}>${state.saving?'Сохраняем назначение…':'Сохранить назначение'}</button><button class="text-button" type="button" data-action="back" ${state.saving?'disabled':''}>Отмена</button></div><p class="quiet" role="status">${state.saving?'Назначение сохраняется. Пожалуйста, подождите.':'После сохранения заявка появится в списке «В работе».'}</p></form>`;return;
 }
 $('#detail').innerHTML=`<div class="detail-top"><span>Заявка № ${r.id}</span><span class="status ${r.status}">${r.status==='new'?'Новая':'В работе'}</span></div><h2>${esc(r.title)}</h2><p class="description">${esc(r.body)}</p><dl class="meta"><dt>Автор</dt><dd>${esc(r.author)}</dd><dt>Создана</dt><dd>${esc(r.created)}</dd><dt>Раздел</dt><dd>${esc(r.category)}</dd>${r.assignee?`<dt>Исполнитель</dt><dd>${esc(r.assignee)}</dd><dt>Срок</dt><dd>${fmt(r.due)}</dd>${r.note?`<dt>Комментарий</dt><dd>${esc(r.note)}</dd>`:''}`:''}</dl><hr class="detail-rule">${r.status==='new'?'<button class="primary" data-action="assign">Назначить исполнителя</button><p class="quiet">Выберите человека и срок. Заявка перейдёт в работу после сохранения.</p>':'<p class="quiet">Назначение сохранено в этом учебном пространстве.</p>'}`;
}
function render(){renderQueue();renderDetail();$('#search').value=state.q;$('#search').disabled=state.saving;$('#clear-search').disabled=state.saving;document.querySelectorAll('.filter,.request-open').forEach(b=>b.disabled=state.saving);$('#simulate-error').disabled=state.saving;$('#reset-demo').disabled=state.saving;$('#simulate-error').setAttribute('aria-pressed',String(state.failNext));$('#simulate-error').textContent=state.failNext?'Ошибка включена для следующего сохранения':'Включить ошибку сохранения';}
document.addEventListener('click',e=>{
 const b=e.target.closest('[data-action]');if(!b||state.saving)return;const a=b.dataset.action;
 if(a==='filter'){state.filter=b.dataset.value;reconcileSelection();writeURL();render();document.querySelector(`[data-action="filter"][data-value="${state.filter}"]`).focus();return;}
 if(a==='open'){state.selected=Number(b.dataset.value);state.step='details';state.error='';state.errors={};}
 if(a==='assign'){state.step='assign';state.error='';state.errors={};}
 if(a==='back'){state.step='details';state.error='';state.errors={};}
 if(a==='active-list'){state.filter='active';state.q='';state.step='details';}
 if(a==='new-list'){state.filter='new';state.q='';state.selected=requests.find(x=>x.status==='new')?.id??null;state.step='details';}
 writeURL();render();focusPanel();
});
$('#search').addEventListener('input',e=>{if(state.saving){e.target.value=state.q;return;}state.q=e.target.value;const changed=reconcileSelection();writeURL(true);renderQueue();if(changed)renderDetail();});
$('#clear-search').onclick=()=>{if(state.saving)return;state.q='';$('#search').value='';reconcileSelection();writeURL(true);renderQueue();renderDetail();$('#search').focus();};
document.addEventListener('input',e=>{if(e.target.closest('#assignment'))draft()[e.target.name]=e.target.value;});
document.addEventListener('change',e=>{if(e.target.closest('#assignment'))draft()[e.target.name]=e.target.value;});
document.addEventListener('submit',async e=>{
 if(e.target.id!=='assignment')return;e.preventDefault();if(state.saving)return;
 const requestId=state.selected,d={...draft()};state.errors={};state.error='';
 if(!people.includes(d.assignee))state.errors.assignee='Выберите исполнителя из списка.';
 if(!/^\d{4}-\d{2}-\d{2}$/.test(d.due)||d.due<'2026-10-25')state.errors.due='Выберите дату не раньше 25 октября.';
 if(Object.keys(state.errors).length){renderDetail();$('#'+Object.keys(state.errors)[0]).focus();return;}
 state.saving=true;render();await new Promise(r=>setTimeout(r,400));state.saving=false;
 if(state.failNext){state.failNext=false;state.error='Не удалось сохранить назначение. Заполненные данные остались на месте. Попробуйте ещё раз.';render();$('#detail .error-banner').tabIndex=-1;$('#detail .error-banner').focus();return;}
 const r=requests.find(entry=>entry.id===requestId);if(!r){state.error='Заявка больше недоступна. Вернитесь к списку и выберите её заново.';state.step='details';render();return;}Object.assign(r,{status:'active',assignee:d.assignee,due:d.due,note:d.note});state.step=state.selected===requestId?'success':'details';render();focusPanel();
});
$('#simulate-error').onclick=()=>{if(state.saving)return;state.failNext=!state.failNext;$('#demo-status').textContent=state.failNext?'Следующее сохранение покажет ошибку. После неё можно повторить действие.':'Проверка ошибки выключена.';render();};
$('#reset-demo').onclick=()=>{if(state.saving)return;requests=structuredClone(seed);state={filter:'new',q:'',selected:104,step:'details',drafts:{},errors:{},error:'',saving:false,failNext:false};writeURL(true);$('#demo-status').textContent='Демонстрация начата заново.';render();};
window.addEventListener('popstate',()=>{if(state.saving){writeURL(true);return;}readURL();reconcileSelection();render();focusPanel();});
readURL();reconcileSelection();writeURL(true);render();
