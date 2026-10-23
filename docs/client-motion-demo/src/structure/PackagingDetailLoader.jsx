import React, {useEffect, useState} from 'react';

// Keep the renderer, scene and detail styles out of the collection's initial load.
export default function PackagingDetailLoader(props) {
  const [Detail, setDetail] = useState(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setFailed(false);
    import('./PackagingDetail.jsx').then(module => {
      if (active) setDetail(() => module.default);
    }).catch(() => {if (active) setFailed(true);});
    return () => {active = false;};
  }, [attempt]);
  if (Detail) return <Detail {...props}/>;
  const zh = props.lang === 'zh';
  return <div className="packaging-shell" aria-busy={!failed}>
    <button className="packaging-shell-back" onClick={props.onClose}>{zh ? '返回产品' : 'Back to collection'}</button>
    <div role="status"><p>{failed ? (zh ? '产品结构暂时无法加载' : 'Product structure is unavailable') : (zh ? '正在准备产品结构' : 'Preparing the product structure')}</p>
      {failed && <button onClick={() => setAttempt(value => value + 1)}>{zh ? '重新加载' : 'Try again'}</button>}
      <button onClick={props.onOriginal}>{zh ? '查看原海报' : 'View original poster'}</button>
    </div>
  </div>;
}
