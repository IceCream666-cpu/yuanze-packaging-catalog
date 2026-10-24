const cards=[...document.querySelectorAll('article')];
document.querySelector('#search').addEventListener('input',event=>{
 const query=event.target.value.trim().toLocaleLowerCase();
 cards.forEach(card=>{card.hidden=!card.dataset.name.toLocaleLowerCase().includes(query);});
 document.querySelector('#empty').hidden=cards.some(card=>!card.hidden);
});
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{
 document.querySelectorAll('[data-view]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));
 cards.forEach(card=>{const img=card.querySelector('img');img.src=img.dataset[button.dataset.view];img.alt=card.querySelector('h2').textContent+' '+({closed:'模型合拢预览',open:'模型展开预览',poster:'原海报'})[button.dataset.view];});
}));
