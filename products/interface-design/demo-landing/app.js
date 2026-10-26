(() => {
  'use strict';
  const KEY = 'interface-design.za-kray.plan.v1';
  const routes = {
    shore: {name:'Каменный берег', code:'01', distance:'2,8', description:'Открытый берег и длинная остановка у воды.', steady:'45-60', slow:'70-90', path:'M105 319C143 284 127 240 181 220S147 167 207 138 224 80 267 65', start:'105 319', end:'267 65', endLabel:'ВИД НА ВОДУ'},
    ridge: {name:'Сосновый гребень', code:'02', distance:'4,1', description:'Лесная тропа и открытая точка над кронами.', steady:'70-90', slow:'100-120', path:'M105 319C169 330 139 279 217 273S318 289 345 237 292 175 356 154 392 95 450 79', start:'105 319', end:'450 79', endLabel:'ВИД НА ЛЕС'}
  };
  const $ = selector => document.querySelector(selector);
  const $$ = selector => [...document.querySelectorAll(selector)];
  const dialog = $('#planner');
  let routeId = 'shore';
  let pace = 'steady';
  let saved = null;
  let trigger = null;
  let objectURL = null;

  function validPlan(value) {
    return value && value.version === 1 && Object.hasOwn(routes,value.route) && ['steady','slow'].includes(value.pace);
  }
  try {
    const value = JSON.parse(localStorage.getItem(KEY));
    if (validPlan(value)) saved = {version:1, route:value.route, pace:value.pace};
  } catch (_) { /* Browsing and downloading do not depend on storage. */ }

  function announce(message) { $('[data-live-status]').textContent = message; }
  function currentPlan() { return {version:1, route:routeId, pace}; }
  function render() {
    const route = routes[routeId];
    $$('[data-route]').forEach(button => {
      const selected = button.dataset.route === routeId;
      button.classList.toggle('is-selected',selected);
      button.setAttribute('aria-pressed',String(selected));
    });
    $$('[name="planner-route"]').forEach(input => { input.checked = input.value === routeId; });
    $$('[name="pace"]').forEach(input => { input.checked = input.value === pace; });
    $('[data-map-panel]').classList.toggle('is-ridge',routeId === 'ridge');
    $('[data-map-name]').textContent = route.name;
    $('[data-map-code]').textContent = 'ПЛАН / ' + route.code;
    $('[data-map-description]').textContent = route.description;
    $('[data-map-time]').textContent = route[pace] + ' мин';
    $('[data-planned-time]').textContent = route[pace] + ' минут';
    $('[data-map-route]').setAttribute('d',route.path);
    $('[data-route-underlay]').setAttribute('d',route.path);
    $('[data-map-start]').setAttribute('transform','translate(' + route.start + ')');
    $('[data-map-end]').setAttribute('transform','translate(' + route.end + ')');
    const endLabel = $('[data-map-end-label]');
    endLabel.textContent = route.endLabel;
    endLabel.setAttribute('x',routeId === 'ridge' ? '393' : '288');
    endLabel.setAttribute('y',routeId === 'ridge' ? '48' : '70');
    $('#map-title').textContent = 'Схема маршрута ' + route.name;
    $('[data-success-name]').textContent = route.name;
    $('[data-success-details]').textContent = route.distance + ' км / ' + (pace === 'slow' ? 'без спешки' : 'обычный темп') + ' / ' + route[pace] + ' минут';
    $('[data-saved-count]').textContent = saved ? '1' : '0';
    $('[data-open-saved]').setAttribute('aria-label',saved ? 'Открыть сохранённый план' : 'Собрать свой план');
  }
  function clearError() {
    $('[data-plan-error]').hidden = true;
    $('[data-plan-error]').textContent = '';
    $('[data-save-plan]').firstChild.textContent = 'Сохранить план ';
  }
  function setStage(success) {
    $('[data-plan-setup]').hidden = success;
    $('[data-plan-success]').hidden = !success;
    $('[data-stage-label]').textContent = success ? 'СОХРАНЕНО В ЭТОМ БРАУЗЕРЕ' : 'ВЫБОР МАРШРУТА';
    $('#planner-title').textContent = success ? 'План готов.' : 'Куда хочется?';
    $('.planner-bottom').hidden = success;
    clearError();
  }
  function openPlanner(button, preferSaved) {
    trigger = button;
    if (preferSaved && saved) {
      routeId = saved.route;
      pace = saved.pace;
    }
    render();
    setStage(Boolean(preferSaved && saved));
    if (!dialog.open) dialog.showModal();
    document.body.classList.add('modal-open');
    $('#planner-title').focus({preventScroll:true});
  }
  function closePlanner() { dialog.close(); }
  function chooseRoute(id, announceChange = true) {
    if (!Object.hasOwn(routes,id)) return;
    routeId = id;
    clearError();
    render();
    if (announceChange) announce('Выбран маршрут: ' + routes[id].name);
  }

  $$('[data-open-planner]').forEach(button => button.addEventListener('click',() => openPlanner(button,false)));
  $('[data-open-saved]').addEventListener('click',event => openPlanner(event.currentTarget,true));
  $('[data-close-planner]').addEventListener('click',closePlanner);
  dialog.addEventListener('click',event => { if (event.target === dialog) closePlanner(); });
  dialog.addEventListener('close',() => {
    document.body.classList.remove('modal-open');
    if (trigger && trigger.isConnected) trigger.focus({preventScroll:true});
  });
  $$('[data-route]').forEach(button => button.addEventListener('click',() => chooseRoute(button.dataset.route)));
  $$('[name="planner-route"]').forEach(input => input.addEventListener('change',() => chooseRoute(input.value)));
  $$('[name="pace"]').forEach(input => input.addEventListener('change',() => { pace = input.value; clearError(); render(); }));
  $('[data-save-plan]').addEventListener('click',() => {
    const plan = currentPlan();
    try {
      localStorage.setItem(KEY,JSON.stringify(plan));
      saved = {...plan};
      render();
      setStage(true);
      $('#planner-title').focus({preventScroll:true});
      announce('План сохранён: ' + routes[plan.route].name);
    } catch (_) {
      const error = $('[data-plan-error]');
      error.textContent = 'Не удалось сохранить план в этом браузере. Повторите попытку или скачайте памятку без сохранения.';
      error.hidden = false;
      $('[data-save-plan]').firstChild.textContent = 'Повторить сохранение ';
    }
  });
  $('[data-edit-plan]').addEventListener('click',() => { setStage(false); $('[name="planner-route"]:checked').focus(); });
  $$('[data-download-plan]').forEach(button => button.addEventListener('click',() => {
    const route = routes[routeId];
    const text = ['ЗА КРАЙ / УЧЕБНЫЙ ПЛАН','',route.name,'Длина: ' + route.distance + ' км','Темп: ' + (pace === 'slow' ? 'без спешки' : 'обычный'),'Время: ' + route[pace] + ' минут','',route.description,'','Это вымышленный маршрут для демонстрации интерфейса.','Он не является географической картой, навигацией или записью на экскурсию.','Никакие данные не отправлены.'].join('\n');
    if (objectURL) URL.revokeObjectURL(objectURL);
    objectURL = URL.createObjectURL(new Blob(['\uFEFF' + text],{type:'text/plain;charset=utf-8'}));
    const link = document.createElement('a');
    link.href = objectURL;
    link.download = 'za-kray-plan-' + routeId + '.txt';
    document.body.append(link);
    link.click();
    link.remove();
    announce('Подготовлена памятка: ' + route.name);
  }));
  window.addEventListener('pagehide',() => { if (objectURL) URL.revokeObjectURL(objectURL); });
  render();
})();
