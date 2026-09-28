export const rules={submit:{from:['draft'],to:'pending',roles:['sales','manager'],title:'提交样品需求'},start:{from:['pending','rework'],to:'making',roles:['lab','manager'],title:'实验室开始制作'},complete:{from:['making'],to:'review',roles:['lab','manager'],title:'实验室提交制作结果'},reject:{from:['review'],to:'rework',roles:['sales','manager'],title:'业务员退回调整'},approve:{from:['review'],to:'ready',roles:['sales','manager'],title:'业务员审核可寄出'},ship:{from:['ready'],to:'feedback',roles:['sales','manager'],title:'登记模拟寄样'},confirm:{from:['feedback'],to:'confirmed',roles:['sales','manager'],title:'记录客户确认'},adjust:{from:['feedback','confirmed','review','ready'],to:'pending',roles:['sales','manager'],title:'发起下一轮调整'}};
export function transition(record,action,payload={},role='sales'){
 const r=rules[action];if(!r||!r.from.includes(record.status))throw new Error('当前状态不能进行此操作');if(!r.roles.includes(role))throw new Error('请切换到对应岗位的演示视角');
 if(['reject','adjust','complete','confirm'].includes(action)&&!String(payload.note||'').trim())throw new Error('请填写处理意见');
 if(action==='ship'&&(!String(payload.carrier||'').trim()||!String(payload.tracking||'').trim()))throw new Error('请填写模拟快递名称及单号');
 if(action==='complete'&&!String(payload.formula||'').trim())throw new Error('请填写本次实际制作使用的配方版本');
 if(action==='adjust'&&!/^\d{4}-\d{2}-\d{2}$/.test(payload.due||''))throw new Error('请填写下一轮期望完成日期');
 const n=structuredClone(record);n.history??=[];n.versions??=[];
 n.history.unshift({title:r.title,note:payload.note||([payload.carrier,payload.tracking].filter(Boolean).join(' · '))||'已完成本步骤',time:new Date().toLocaleString('zh-CN',{hour12:false}),round:n.round});
 if(action==='adjust'){n.round++;n.req=payload.note.trim();n.due=payload.due;n.type='配方调整';n.baseFormula=n.versions.at(-1)?.code;n.versions.push({round:n.round,code:'待实验室确认',req:n.req,note:'新一轮需求已提交，实际配方待实验室确认。'});}
 if(action==='complete'){const latest=n.versions.at(-1);if(latest?.code==='待实验室确认'){latest.code=payload.formula.trim();latest.note=payload.note.trim();}else n.versions.push({round:n.round,code:payload.formula.trim(),req:n.req,note:payload.note.trim()});}
 if(action==='ship'){n.shipments??=[];n.shipments.push({round:n.round,formula:n.versions.at(-1)?.code,carrier:payload.carrier,tracking:payload.tracking,time:new Date().toLocaleString('zh-CN')});}
 if(action==='confirm'){n.confirmations??=[];n.confirmations.push({round:n.round,formula:n.versions.at(-1)?.code,note:payload.note,time:new Date().toLocaleString('zh-CN')});}
 n.status=r.to;return n;
}
