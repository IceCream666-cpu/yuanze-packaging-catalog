/* User-supplied company material shared by the preview and authenticated showroom. */
window.YuanzeCompanyContent = {
  suppliedAt: '2026-09-30',
  status: 'design-preview',
  claimsSource: 'user-provided; not independently verified',
  originalIntroductionEn: 'We research, develop, and manufacture skincare, body care, hair care, and sun protection products for brands and retailers in over 30 countries worldwide. Our products are FDA-registered and certified to ISO 22716 and GMPC standards, with a formulation science foundation built on 14 years of experience. From your first private label line to millions of retail items, you need only partner with one trusted collaborator.',
  introductionAdaptation: 'Certification wording refers to the company manufacturing management system. FDA registration is not asserted in display copy because the supplied ISO/GMPC certificates do not establish that registration. The original supplied introduction is preserved above.',
  images: {
    showroom: {src: '/showroom/assets/showroom.png', width: 1448, height: 1086, originalName: '展厅(1).png'},
    reception: {src: '/showroom/assets/reception.png', width: 1471, height: 1069, originalName: '大门(1).png'}
  },
  certificates: {
    iso22716: {
      number: 'HBPCER20260291', standard: 'ISO 22716:2007',
      holder: '广州源泽药业有限公司', holderEn: 'Guangzhou Yuanze Pharmaceutical Co., Ltd.',
      issuer: 'Intertek Testing Services', issuedAt: '2026-06-25', expiresAt: '2029-06-15',
      versions: {
        zh: {src: '/showroom/assets/certificates/iso22716-zh.png', pdf: '/showroom/assets/certificates/iso22716-zh.pdf', width: 990, height: 1400},
        en: {src: '/showroom/assets/certificates/iso22716-en.png', pdf: '/showroom/assets/certificates/iso22716-en.pdf', width: 990, height: 1400}
      }
    },
    gmpc: {
      number: 'HBPCER20260292', standard: 'COSMETIC GOOD MANUFACTURING PRACTICE GUIDELINES (2025) PUBLISHED BY U.S. FOOD AND DRUG ADMINISTRATION',
      holder: '广州源泽药业有限公司', holderEn: 'Guangzhou Yuanze Pharmaceutical Co., Ltd.',
      issuer: 'Intertek Testing Services', issuedAt: '2026-06-25', expiresAt: '2029-06-15',
      versions: {
        zh: {src: '/showroom/assets/certificates/gmpc-zh.png', pdf: '/showroom/assets/certificates/gmpc-zh.pdf', width: 990, height: 1400},
        en: {src: '/showroom/assets/certificates/gmpc-en.png', pdf: '/showroom/assets/certificates/gmpc-en.pdf', width: 990, height: 1400}
      }
    }
  },
  posterBanners: [
    {id:'pdrn-capsule-cream', src:'/showroom/assets/poster-banners/01-pdrn-capsule-cream.webp', width:1983, height:793, title:{zh:'liaose · PDRN 胶囊面霜', en:'liaose · PDRN CAPSULE CREAM'}},
    {id:'body-care-collection', src:'/showroom/assets/poster-banners/02-body-care-collection.webp', width:2089, height:753, title:{zh:'liaose · 身体护理系列：薰衣草双瓶、茶树及氨基酸沐浴露、精油磨砂膏', en:'liaose · THE BODY CARE DUO · TEA TREE BODY WASH · AMINO ACID BODY WASH · AHA & ESSENTIAL OIL BODY SCRUB'}},
    {id:'cherry-blossom-gift-set', src:'/showroom/assets/poster-banners/03-cherry-blossom-gift-set.webp', width:2048, height:768, title:{zh:'liaose · 樱花香氛护理礼盒', en:'liaose · CHERRY BLOSSOM FRAGRANCE GIFT SET'}},
    {id:'hand-care-collection', src:'/showroom/assets/poster-banners/04-hand-care-collection.webp', width:2048, height:768, title:{zh:'liaose · 香氛洗手液与玉兰乳香护手油', en:'liaose · FRAGRANCED HAND WASH · MAGNOLIA & FRANKINCENSE HAND OIL'}},
    {id:'daylight-still', src:'/showroom/assets/poster-banners/05-daylight-still.webp', width:1983, height:793, title:{zh:'liaose · DAYLIGHT 香水与 STILL 草本空间喷雾', en:'liaose · DAYLIGHT · STILL · EAU DE PARFUM · HERBAL ROOM SPRAY'}}
  ],
  zh: {
    title: 'YUANZE · 客户展厅',
    previewTitle: 'YUANZE · 客户展厅预览',
    logout: '退出登录',
    loggingOut: '正在退出…',
    logoutError: '暂时无法退出，请检查网络后重试。',
    receptionTeam: '源泽 · 客户接待',
    inquiryTitle: '您的意向清单',
    inquiryHint: '可在产品页选择多款包材，再将清单交给业务员咨询。',
    inquiryEmpty: '还未选择包材',
    continueSelection: '继续选型',
    inquiryNote: '补充您的需求',
    inquiryPlaceholder: '例如：需要的容量、数量、使用产品或定制要求',
    copyInquiry: '复制咨询清单',
    inquiryCopied: '已复制，可粘贴发送给业务员。',
    inquiryCopyFailed: '无法自动复制，请手动选择清单内容。',
    inquiryLocal: '清单仅保留在本次浏览中；复制后可自行发送给业务员。',
    inquiryProduct: '产品编号',
    inquiryCapacity: '净含量',
    preview: '客户界面预览 · 尚未上线',
    language: 'English',
    languageLabel: '切换为英文',
    tagline: '研发 · 配方 · 包材',
    headline: '从产品构想，\n到品牌呈现。',
    summary: '为全球品牌提供护肤、身体护理、洗护发与防晒产品的研发及制造服务。',
    explore: '探索产品',
    productViews: '产品浏览方式',
    posterTab: '产品海报',
    catalogTab: '包材选型',
    posterTitle: '优质产品海报',
    posterDescription: '精选产品系列，点开查看完整海报。',
    posterNote: '包材规格请进入包材选型查看。',
    bannerLabel: '产品系列轮播',
    previousBanner: '上一张背景图',
    nextBanner: '下一张背景图',
    pauseBanner: '暂停轮播',
    resumeBanner: '继续轮播',
    bannerImageError: '背景图暂时无法加载，可切换下一张。',
    posterCategories: '海报类别',
    allPosters: '全部',
    posterCount: '{count} 张海报 · 共 {total} 张',
    posterOpen: '查看完整海报：{title}',
    posterView: '查看完整海报',
    posterPosition: '{current} / {total}',
    posterImageError: '图片暂时无法加载，请稍后重试。',
    enterCatalog: '进入包材选型',
    previousPoster: '上一张',
    nextPoster: '下一张',
    aboutLink: '了解源泽',
    showroomTitle: '在源泽，发现更多产品可能',
    showroomCaption: '源泽产品展厅',
    showroomAlt: '源泽产品展厅，陈列护肤及化妆品产品的展示空间',
    showroomEnlarge: '放大查看源泽产品展厅',
    years: '年配方研发经验',
    countries: '个国家的品牌与零售商',
    capabilitiesTitle: '围绕您的品牌，提供产品配套',
    capabilities: ['OEM', 'ODM', 'OBM', 'private label'],
    aboutTitle: '一个伙伴，连接产品的每一步',
    receptionCaption: '广州源泽药业有限公司 · 公司前台',
    receptionAlt: '广州源泽药业有限公司前台，墙面展示公司名称及源泽标志',
    receptionEnlarge: '放大查看公司前台',
    introduction: '我们为全球超过 30 个国家的品牌及零售商提供护肤、身体护理、洗护发和防晒产品的研究、开发与制造服务。公司的生产管理体系通过 Intertek 的 ISO 22716:2007 和 GMPC 认证，配方科学基础源于 14 年的经验积累。从您的首个自有品牌产品系列，到数百万件零售产品，您只需携手一位值得信赖的合作伙伴。',
    fullIntroduction: '阅读完整公司简介',
    certificatesTitle: '质量标准与证书',
    certificatesHelp: '点开查看证书，或阅读原始 PDF。',
    iso22716Caption: 'ISO 22716:2007 · 中文证书',
    gmpcCaption: 'GMPC · 中文证书',
    iso22716Enlarge: '放大查看 ISO 22716 中文证书',
    gmpcEnlarge: '放大查看 GMPC 中文证书',
    openPdf: '查看原始 PDF',
    certificateExpiry: '证书有效期至',
    packagingTitle: '为下一款产品，找到合适的包材',
    packagingCopy: '按材质、容量、瓶型与用途探索包材，逐步完善您的产品方案。',
    packagingButton: '进入包材展厅',
    packagingHint: '打开现有网站，需使用客户账号登录',
    contactTitle: '聊聊您的下一款产品',
    contactCopy: '研发、OEM／ODM 或包材选型，我们期待了解您的需求。',
    contactPending: '专属业务员与公司统一接待联系方式待补充',
    home: '首页',
    products: '产品',
    contact: '联系',
    navLabel: '主导航',
    close: '关闭大图',
    footer: '广州源泽药业有限公司'
  },
  en: {
    title: 'YUANZE · Customer showroom',
    previewTitle: 'YUANZE · Customer showroom preview',
    logout: 'Log out',
    loggingOut: 'Logging out…',
    logoutError: 'Unable to log out. Check your connection and try again.',
    receptionTeam: 'YUANZE · Customer team',
    inquiryTitle: 'Your shortlist',
    inquiryHint: 'Select packaging on the Products page and share your shortlist with your sales representative.',
    inquiryEmpty: 'No packaging selected yet',
    continueSelection: 'Continue exploring',
    inquiryNote: 'Tell us what you need',
    inquiryPlaceholder: 'Capacity, quantity, product application or customisation requirements',
    copyInquiry: 'Copy enquiry',
    inquiryCopied: 'Copied. Paste and send it to your sales representative.',
    inquiryCopyFailed: 'Unable to copy automatically. Please select and copy the details.',
    inquiryLocal: 'This shortlist stays in your current browsing session. Copy it to contact your sales representative.',
    inquiryProduct: 'Product code',
    inquiryCapacity: 'Net content',
    preview: 'Customer showroom preview · not published',
    language: '中文',
    languageLabel: 'Switch to Chinese',
    tagline: 'RESEARCH · FORMULA · PACKAGING',
    headline: 'From product concept\nto your brand.',
    summary: 'Research, development and manufacturing of skincare, body care, hair care and sun protection for brands worldwide.',
    explore: 'Explore products',
    productViews: 'Product views',
    posterTab: 'Product posters',
    catalogTab: 'Packaging selection',
    posterTitle: 'Product inspiration',
    posterDescription: 'Explore selected product collections. Open a poster to see it in full.',
    posterNote: 'Explore packaging selection for formats and specifications.',
    bannerLabel: 'Product collection carousel',
    previousBanner: 'Previous banner',
    nextBanner: 'Next banner',
    pauseBanner: 'Pause slideshow',
    resumeBanner: 'Resume slideshow',
    bannerImageError: 'This background is unavailable. Try the next slide.',
    posterCategories: 'Poster categories',
    allPosters: 'All',
    posterCount: '{count} posters · {total} total',
    posterOpen: 'View full poster: {title}',
    posterView: 'View full poster',
    posterPosition: '{current} / {total}',
    posterImageError: 'This image is unavailable. Please try again later.',
    enterCatalog: 'Explore packaging',
    previousPoster: 'Previous',
    nextPoster: 'Next',
    aboutLink: 'Discover Yuanze',
    showroomTitle: 'Discover possibilities at Yuanze',
    showroomCaption: 'The Yuanze product showroom',
    showroomAlt: 'The Yuanze showroom with skincare and cosmetics displayed throughout the space',
    showroomEnlarge: 'Enlarge the Yuanze showroom photo',
    years: 'years of formulation experience',
    countries: 'countries served: brands & retailers',
    capabilitiesTitle: 'Product expertise for your brand',
    capabilities: ['OEM', 'ODM', 'OBM', 'private label'],
    aboutTitle: 'One partner, from concept onward',
    receptionCaption: 'Guangzhou Yuanze Pharmaceutical Co., Ltd. · Reception',
    receptionAlt: 'The Yuanze company reception with its name and logo on the wall',
    receptionEnlarge: 'Enlarge the company reception photo',
    introduction: 'We research, develop, and manufacture skincare, body care, hair care, and sun protection products for brands and retailers in over 30 countries worldwide. Our manufacturing management system is certified by Intertek to ISO 22716:2007 and Cosmetic Good Manufacturing Practice guidelines, with a formulation science foundation built on 14 years of experience. From your first private label line to millions of retail items, you need only partner with one trusted collaborator.',
    fullIntroduction: 'Read our full introduction',
    certificatesTitle: 'Quality standards & certificates',
    certificatesHelp: 'Tap to enlarge a certificate or read the original PDF.',
    iso22716Caption: 'ISO 22716:2007 · English certificate',
    gmpcCaption: 'GMPC · English certificate',
    iso22716Enlarge: 'Enlarge the ISO 22716 English certificate',
    gmpcEnlarge: 'Enlarge the GMPC English certificate',
    openPdf: 'Open original PDF',
    certificateExpiry: 'Certificate expires',
    packagingTitle: 'Find packaging for your next product',
    packagingCopy: 'Explore materials, capacities, shapes and uses to develop your product concept.',
    packagingButton: 'Open the packaging gallery',
    packagingHint: 'Opens the existing website; customer sign-in required',
    contactTitle: 'Let’s talk about your next product',
    contactCopy: 'Tell us about your R&D, OEM / ODM or packaging needs.',
    contactPending: 'Representative and company contact details to be supplied',
    home: 'Home',
    products: 'Products',
    contact: 'Contact',
    navLabel: 'Main navigation',
    close: 'Close photo',
    footer: 'YUANZE COSMETICS'
  }
};

/* User-supplied poster artwork. No catalogue SKU or price is inferred. */
window.YuanzeProductPosters = {
  "categories": [
    {
      "id": "face",
      "zh": "面部护理",
      "en": "Face care"
    },
    {
      "id": "hair",
      "zh": "头发护理",
      "en": "Hair care"
    },
    {
      "id": "body",
      "zh": "身体护理",
      "en": "Body care"
    },
    {
      "id": "fragrance",
      "zh": "香氛",
      "en": "Fragrance"
    },
    {
      "id": "oral",
      "zh": "口腔护理",
      "en": "Oral care"
    },
    {
      "id": "sets",
      "zh": "护理套装",
      "en": "Care sets"
    }
  ],
  "items": [
    {
      "id": "poster-001",
      "category": "face",
      "title": {
        "zh": "胶原水凝胶面膜 · 青绿",
        "en": "Collagen hydrogel mask · Teal"
      },
      "src": "/showroom/assets/posters/poster-001.webp",
      "thumbnail": "/showroom/assets/posters/poster-001-thumb.webp",
      "width": 1254,
      "height": 1254
    },
    {
      "id": "poster-002",
      "category": "face",
      "title": {
        "zh": "胶原水凝胶面膜 · 紫色",
        "en": "Collagen hydrogel mask · Purple"
      },
      "src": "/showroom/assets/posters/poster-002.webp",
      "thumbnail": "/showroom/assets/posters/poster-002-thumb.webp",
      "width": 1254,
      "height": 1254
    },
    {
      "id": "poster-003",
      "category": "face",
      "title": {
        "zh": "胶原水凝胶面膜 · 黄色",
        "en": "Collagen hydrogel mask · Yellow"
      },
      "src": "/showroom/assets/posters/poster-003.webp",
      "thumbnail": "/showroom/assets/posters/poster-003-thumb.webp",
      "width": 1254,
      "height": 1254
    },
    {
      "id": "poster-004",
      "category": "hair",
      "title": {
        "zh": "护发油系列",
        "en": "Hair oil collection"
      },
      "src": "/showroom/assets/posters/poster-004.webp",
      "thumbnail": "/showroom/assets/posters/poster-004-thumb.webp",
      "width": 1672,
      "height": 941
    },
    {
      "id": "poster-005",
      "category": "sets",
      "title": {
        "zh": "WHT Glow 护理礼盒",
        "en": "WHT Glow care gift set"
      },
      "src": "/showroom/assets/posters/poster-005.webp",
      "thumbnail": "/showroom/assets/posters/poster-005-thumb.webp",
      "width": 1122,
      "height": 1402
    },
    {
      "id": "poster-006",
      "category": "fragrance",
      "title": {
        "zh": "Lunéo Dawn 香水",
        "en": "Lunéo Dawn perfume"
      },
      "src": "/showroom/assets/posters/poster-006.webp",
      "thumbnail": "/showroom/assets/posters/poster-006-thumb.webp",
      "width": 1086,
      "height": 1448
    },
    {
      "id": "poster-007",
      "category": "fragrance",
      "title": {
        "zh": "Noiré Glow 香水",
        "en": "Noiré Glow perfume"
      },
      "src": "/showroom/assets/posters/poster-007.webp",
      "thumbnail": "/showroom/assets/posters/poster-007-thumb.webp",
      "width": 1122,
      "height": 1402
    },
    {
      "id": "poster-008",
      "category": "oral",
      "title": {
        "zh": "牙膏系列",
        "en": "Toothpaste collection"
      },
      "src": "/showroom/assets/posters/poster-008.webp",
      "thumbnail": "/showroom/assets/posters/poster-008-thumb.webp",
      "width": 1122,
      "height": 1402
    },
    {
      "id": "poster-009",
      "category": "face",
      "title": {
        "zh": "精华液系列",
        "en": "Serum collection"
      },
      "src": "/showroom/assets/posters/poster-009.webp",
      "thumbnail": "/showroom/assets/posters/poster-009-thumb.webp",
      "width": 1254,
      "height": 1254
    },
    {
      "id": "poster-010",
      "category": "face",
      "title": {
        "zh": "PDRN 胶囊面霜",
        "en": "PDRN capsule cream"
      },
      "src": "/showroom/assets/posters/poster-010.webp",
      "thumbnail": "/showroom/assets/posters/poster-010-thumb.webp",
      "width": 1254,
      "height": 1254
    },
    {
      "id": "poster-011",
      "category": "sets",
      "title": {
        "zh": "Pink Cloud 身体护理套装",
        "en": "Pink Cloud body care set"
      },
      "src": "/showroom/assets/posters/poster-011.webp",
      "thumbnail": "/showroom/assets/posters/poster-011-thumb.webp",
      "width": 1254,
      "height": 1254
    },
    {
      "id": "poster-012",
      "category": "body",
      "title": {
        "zh": "身体磨砂膏 · 黄粉",
        "en": "Body scrub · Yellow & pink"
      },
      "src": "/showroom/assets/posters/poster-012.webp",
      "thumbnail": "/showroom/assets/posters/poster-012-thumb.webp",
      "width": 1254,
      "height": 1254
    },
    {
      "id": "poster-013",
      "category": "body",
      "title": {
        "zh": "身体磨砂膏 · 珊瑚青绿",
        "en": "Body scrub · Coral & aqua"
      },
      "src": "/showroom/assets/posters/poster-013.webp",
      "thumbnail": "/showroom/assets/posters/poster-013-thumb.webp",
      "width": 1254,
      "height": 1254
    },
    {
      "id": "poster-014",
      "category": "body",
      "title": {
        "zh": "身体磨砂系列",
        "en": "Body scrub collection"
      },
      "src": "/showroom/assets/posters/poster-014.webp",
      "thumbnail": "/showroom/assets/posters/poster-014-thumb.webp",
      "width": 1600,
      "height": 983
    },
    {
      "id": "poster-032",
      "category": "body",
      "title": {
        "zh": "liaose 氨基酸沐浴露",
        "en": "liaose amino acid body wash"
      },
      "src": "/showroom/assets/posters/poster-032.webp",
      "thumbnail": "/showroom/assets/posters/poster-032-thumb.webp",
      "width": 1024,
      "height": 1536
    },
    {
      "id": "poster-033",
      "category": "body",
      "title": {
        "zh": "liaose 茶树沐浴露",
        "en": "liaose tea tree body wash"
      },
      "src": "/showroom/assets/posters/poster-033.webp",
      "thumbnail": "/showroom/assets/posters/poster-033-thumb.webp",
      "width": 1024,
      "height": 1536
    },
    {
      "id": "poster-034",
      "category": "hair",
      "title": {
        "zh": "liaose 山茶花护发素",
        "en": "liaose camellia conditioner"
      },
      "src": "/showroom/assets/posters/poster-034.webp",
      "thumbnail": "/showroom/assets/posters/poster-034-thumb.webp",
      "width": 1086,
      "height": 1448
    },
    {
      "id": "poster-035",
      "category": "sets",
      "title": {
        "zh": "liaose 植萃沐浴礼盒",
        "en": "liaose botanical bath gift set"
      },
      "src": "/showroom/assets/posters/poster-035.webp",
      "thumbnail": "/showroom/assets/posters/poster-035-thumb.webp",
      "width": 1086,
      "height": 1448
    },
    {
      "id": "poster-036",
      "category": "face",
      "title": {
        "zh": "liaose 真空瓶系列 · 紫黄",
        "en": "liaose airless packaging · Lilac & yellow"
      },
      "src": "/showroom/assets/posters/poster-036.webp",
      "thumbnail": "/showroom/assets/posters/poster-036-thumb.webp",
      "width": 1086,
      "height": 1448
    },
    {
      "id": "poster-037",
      "category": "body",
      "title": {
        "zh": "liaose 木兰乳香护手油",
        "en": "liaose magnolia & frankincense hand oil"
      },
      "src": "/showroom/assets/posters/poster-037.webp",
      "thumbnail": "/showroom/assets/posters/poster-037-thumb.webp",
      "width": 1086,
      "height": 1448
    },
    {
      "id": "poster-038",
      "category": "face",
      "title": {
        "zh": "liaose 玻尿酸舒缓面霜",
        "en": "liaose hyaluronic acid soothing cream"
      },
      "src": "/showroom/assets/posters/poster-038.webp",
      "thumbnail": "/showroom/assets/posters/poster-038-thumb.webp",
      "width": 1254,
      "height": 1254
    },
    {
      "id": "poster-039",
      "category": "face",
      "title": {
        "zh": "liaose 面部护理系列",
        "en": "liaose face care collection"
      },
      "src": "/showroom/assets/posters/poster-039.webp",
      "thumbnail": "/showroom/assets/posters/poster-039-thumb.webp",
      "width": 1672,
      "height": 941
    },
    {
      "id": "poster-040",
      "category": "sets",
      "title": {
        "zh": "liaose 樱花香氛护理礼盒",
        "en": "liaose cherry blossom fragrance gift set"
      },
      "src": "/showroom/assets/posters/poster-040.webp",
      "thumbnail": "/showroom/assets/posters/poster-040-thumb.webp",
      "width": 1086,
      "height": 1448
    },
    {
      "id": "poster-041",
      "category": "body",
      "title": {
        "zh": "liaose 果酸精油身体磨砂膏",
        "en": "liaose AHA & essential oil body scrub"
      },
      "src": "/showroom/assets/posters/poster-041.webp",
      "thumbnail": "/showroom/assets/posters/poster-041-thumb.webp",
      "width": 1086,
      "height": 1448
    }
  ]
};

(() => {
  'use strict';
  const content = window.YuanzeCompanyContent;
  const posters = window.YuanzeProductPosters || {categories:[], items:[]};
  const toggle = document.getElementById('language-toggle');
  const dialog = document.getElementById('photo-dialog');
  const photo = document.getElementById('expanded-photo');
  const photoCaption = document.getElementById('photo-caption');
  const closePhoto = document.getElementById('close-photo');
  const frame = document.getElementById('catalog-frame');
  const posterView = document.getElementById('poster-view');
  const catalogView = document.getElementById('catalog-view');
  const posterGrid = document.getElementById('poster-grid');
  const posterCategories = document.getElementById('poster-categories');
  const posterControls = document.getElementById('poster-controls');
  const posterPosition = document.getElementById('poster-position');
  const previousPoster = document.getElementById('previous-poster');
  const nextPoster = document.getElementById('next-poster');
  const photoError = document.getElementById('photo-error');
  const banner = document.getElementById('poster-banner');
  const bannerArt = document.getElementById('poster-banner-art');
  const bannerPosition = document.getElementById('banner-position');
  const bannerToggle = document.getElementById('banner-toggle');
  const bannerError = document.getElementById('banner-error');
  const banners = content.posterBanners || [];
  const bannerSlides = [];
  const reducedMotion = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : {matches:false};
  let bannerIndex = 0;
  let bannerPaused = reducedMotion.matches;
  let bannerPauseChosen = false;
  let bannerInView = true;
  let bannerTimer = null;
  const production = document.documentElement.dataset.mode === 'production';
  const logout = document.getElementById('showroom-logout');
  const sessionMessage = document.getElementById('session-message');
  const pages = ['home', 'products', 'contact'];
  let activeRoute = null;
  let shortlist = [];
  let inquiryStatus = '';
  let language = 'zh';
  let selectedPhoto = null;
  let selectedPoster = null;
  let posterCategory = 'all';
  let photoTrigger = null;
  let loggingOut = false;
  let logoutFailed = false;
  let posterObserver = null;
  let viewerRequest = 0;

  function previewURL(source, edge = 512) {
    return source.replace(/assets\/(.+)\.(png|webp)$/, `assets/previews/$1-${edge}.webp`);
  }

  function loadPoster(image) {
    if (image && !image.hasAttribute('src')) image.src = image.dataset.previewSrc;
  }
  document.querySelector('.preview-label').hidden = production;
  logout.hidden = !production;
  try { if ((localStorage.getItem('yuanze-language') || localStorage.getItem('yuanze-mobile-preview-language')) === 'en') language = 'en'; } catch (_) {}

  function scheduleBanner() {
    if (bannerTimer !== null) window.clearTimeout(bannerTimer);
    bannerTimer = null;
    if (!banner || banners.length < 2 || bannerPaused || !bannerInView || document.hidden || dialog.open || activeRoute?.split('?')[0] !== 'products') return;
    bannerTimer = window.setTimeout(() => {
      showBanner(bannerIndex + 1);
      scheduleBanner();
    }, 6000);
  }

  function renderBanner() {
    if (!banner || !banners.length) return;
    const copy = content[language];
    bannerSlides.forEach((slide, index) => {
      const image = slide.querySelector('img');
      const active = index === bannerIndex;
      slide.classList.toggle('is-active', active);
      slide.setAttribute('aria-hidden', String(!active));
      image.setAttribute('aria-hidden', String(!active));
      image.alt = banners[index].title[language];
      slide.setAttribute('aria-label', `${index + 1} / ${banners.length}: ${image.alt}`);
      if (active && activeRoute?.split('?')[0] === 'products') {
        const source=previewURL(image.dataset.src, window.matchMedia?.('(max-width: 760px)').matches ? 512 : 1280);
        if(image.getAttribute('src')!==source)image.src=source;
      }
    });
    bannerPosition.textContent = `${bannerIndex + 1} / ${banners.length}`;
    bannerPosition.setAttribute('aria-live', bannerPaused ? 'polite' : 'off');
    bannerToggle.textContent = copy[bannerPaused ? 'resumeBanner' : 'pauseBanner'];
    bannerToggle.setAttribute('aria-pressed', String(bannerPaused));
    bannerError.hidden = !bannerSlides[bannerIndex]?.classList.contains('image-failed');
  }

  function showBanner(index) {
    if (!banners.length) return;
    bannerIndex = (index + banners.length) % banners.length;
    renderBanner();
  }

  function initializeBanner() {
    if (!banner || !banners.length) return;
    banners.forEach((item, index) => {
      const slide = document.createElement('div');
      slide.className = 'banner-slide';
      slide.setAttribute('role', 'group');
      slide.setAttribute('aria-roledescription', 'slide');
      const image = document.createElement('img');
      image.dataset.bannerSlide = String(index);
      image.dataset.src = item.src;
      image.width = item.width; image.height = item.height;
      image.decoding = 'async';
      image.addEventListener('error', () => {
        slide.classList.add('image-failed');
        if (index === bannerIndex) renderBanner();
      });
      image.addEventListener('load', () => {
        slide.classList.remove('image-failed');
        if (index === bannerIndex) renderBanner();
      });
      slide.append(image); bannerArt.append(slide); bannerSlides.push(slide);
    });
    document.getElementById('banner-previous').addEventListener('click', () => { showBanner(bannerIndex - 1); scheduleBanner(); });
    document.getElementById('banner-next').addEventListener('click', () => { showBanner(bannerIndex + 1); scheduleBanner(); });
    bannerToggle.addEventListener('click', () => {
      bannerPaused = !bannerPaused; bannerPauseChosen = true;
      renderBanner(); scheduleBanner();
    });
    document.addEventListener('visibilitychange', scheduleBanner);
    window.matchMedia?.('(max-width: 760px)').addEventListener?.('change', renderBanner);
    reducedMotion.addEventListener?.('change', event => {
      if (!bannerPauseChosen) bannerPaused = event.matches;
      renderBanner(); scheduleBanner();
    });
    if ('IntersectionObserver' in window) {
      const observer = new window.IntersectionObserver(entries => {
        bannerInView = entries.some(entry => entry.target === banner && entry.isIntersecting);
        scheduleBanner();
      }, {root:posterView, threshold:0});
      observer.observe(banner);
    }
  }

  function notifyLanguage() {
    if (frame.hasAttribute('src')) frame.contentWindow?.postMessage({type:'yuanze-language', language}, location.origin);
  }

  function renderInquiry() {
    const copy = content[language], box = document.getElementById('inquiry-items');
    box.replaceChildren();
    shortlist.forEach(item => {
      const row = document.createElement('div');
      const code = document.createElement('strong');
      const capacity = document.createElement('span');
      code.textContent = item.productCode;
      capacity.textContent = `${copy.inquiryCapacity}: ${item.capacity || '—'}`;
      row.append(code, capacity); box.append(row);
    });
    document.getElementById('inquiry-empty').hidden = shortlist.length > 0;
    document.getElementById('inquiry-status').textContent = inquiryStatus ? copy[inquiryStatus] : '';
  }

  function format(key, values) {
    return content[language][key].replace(/\{(\w+)\}/g, (_, key) => values[key]);
  }

  function filteredPosters() {
    return posters.items.filter(item => posterCategory === 'all' || item.category === posterCategory);
  }

  function posterRoute(category = posterCategory, id = '') {
    const query = new window.URLSearchParams();
    if (category !== 'all') query.set('category', category);
    if (id) query.set('poster', id);
    const suffix = query.toString();
    return `products${suffix ? `?${suffix}` : ''}`;
  }

  // Keep poster state in the URL so Back/Forward can restore category and viewer.
  // The catalogue remains mounted when its subpage is hidden.
  function showPage(route, focus = false) {
    if (activeRoute === route) return;
    activeRoute = route;
    const [path, query = ''] = route.split('?');
    const next = path === 'products/catalog' ? 'products' : pages.includes(path) ? path : 'home';
    const catalog = path === 'products/catalog';
    document.querySelectorAll('[data-page]').forEach(panel => { panel.hidden = panel.dataset.page !== next; });
    document.querySelectorAll('[data-page-navigation] [data-page-link]').forEach(link => {
      if (link.dataset.pageLink === next) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    posterView.hidden = catalog;
    catalogView.hidden = !catalog;
    document.querySelectorAll('[data-product-view]').forEach(link => {
      if (link.dataset.productView === (catalog ? 'catalog' : 'posters')) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    if (next === 'products' && catalog && !frame.hasAttribute('src')) frame.src = frame.dataset.src;
    let poster = null;
    if (next === 'products' && !catalog) {
      const params = new window.URLSearchParams(query);
      posterCategory = posters.categories.some(category => category.id === params.get('category')) ? params.get('category') : 'all';
      renderPosters();
      poster = filteredPosters().find(item => item.id === params.get('poster')) || null;
    }
    const closingPoster = selectedPoster && !poster;
    if (poster) {
      selectedPhoto = null;
      selectedPoster = poster.id;
      photoTrigger = posterGrid.querySelector(`[data-poster-image="${poster.id}"]`);
      updatePhoto();
      if (!dialog.open) { dialog.showModal(); closePhoto.focus(); }
    } else if (selectedPoster) {
      selectedPoster = null;
      if (dialog.open) dialog.close();
    }
    if (focus && !dialog.open && (!closingPoster || !photoTrigger || photoTrigger.closest('[hidden]'))) document.getElementById(`page-${next}`).focus({preventScroll:true});
    renderBanner();
    scheduleBanner();
  }

  function navigate(route, options = {}) {
    const hash = `#/${route}`;
    if (location.hash !== hash) history[options.replace ? 'replaceState' : 'pushState'](options.state || null, '', hash);
    showPage(route, !options.keepFocus);
  }

  function initializePosters() {
    [{id:'all'}, ...posters.categories].forEach(category => {
      const button = document.createElement('button');
      button.type = 'button'; button.dataset.posterCategory = category.id;
      button.addEventListener('click', () => navigate(posterRoute(category.id), {keepFocus:true}));
      posterCategories.append(button);
    });
    if ('IntersectionObserver' in window) {
      posterObserver = new window.IntersectionObserver(entries => {
        if (activeRoute?.split('?')[0] !== 'products') return;
        entries.forEach(entry => {
          if (entry.isIntersecting && !entry.target.closest('[hidden]')) {
            loadPoster(entry.target); posterObserver.unobserve(entry.target);
          }
        });
      }, {root:posterView, rootMargin:'120px 0px', threshold:0});
    }
    posters.items.forEach(item => {
      const card = document.createElement('article');
      card.className = 'poster-card'; card.dataset.posterCard = item.id;
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'poster-card-button'; button.dataset.posterImage = item.id;
      const image = document.createElement('img');
      image.dataset.previewSrc = previewURL(item.src); image.width = item.width; image.height = item.height;
      image.loading = 'lazy'; image.decoding = 'async';
      const details = document.createElement('span'); details.className = 'poster-card-details';
      const title = document.createElement('strong'); title.dataset.posterTitle = item.id;
      const action = document.createElement('span'); action.dataset.copy = 'posterView';
      const error = document.createElement('span'); error.className = 'poster-image-error'; error.dataset.copy = 'posterImageError'; error.hidden = true;
      image.addEventListener('error', () => { image.hidden = true; error.hidden = false; });
      details.append(title, action); button.append(image, error, details); card.append(button); posterGrid.append(card);
      button.addEventListener('click', () => {
        photoTrigger = button;
        navigate(posterRoute(posterCategory, item.id), {state:{yuanzePosterEntry:true}});
      });
    });
  }

  function renderPosters() {
    const visible = filteredPosters();
    posterCategories.querySelectorAll('button').forEach(button => {
      const id = button.dataset.posterCategory;
      button.textContent = id === 'all' ? content[language].allPosters : posters.categories.find(category => category.id === id)[language];
      button.setAttribute('aria-pressed', String(id === posterCategory));
    });
    posters.items.forEach(item => {
      const card = document.querySelector(`[data-poster-card="${item.id}"]`);
      card.hidden = posterCategory !== 'all' && item.category !== posterCategory;
      const image = card.querySelector('img');
      if (card.hidden || activeRoute?.split('?')[0] !== 'products') posterObserver?.unobserve(image);
      else if (!image.hasAttribute('src')) {
        if (posterObserver) posterObserver.observe(image);
        else loadPoster(image);
      }
      card.querySelector('strong').textContent = item.title[language];
      card.querySelector('img').alt = item.title[language];
      card.querySelector('button').setAttribute('aria-label', format('posterOpen', {title:item.title[language]}));
    });
    document.getElementById('poster-count').textContent = format('posterCount', {count:visible.length, total:posters.items.length});
  }

  function updatePhoto() {
    posterControls.hidden = !selectedPoster;
    posterPosition.hidden = !selectedPoster;
    dialog.classList.toggle('poster-dialog', Boolean(selectedPoster));
    const poster = posters.items.find(item => item.id === selectedPoster);
    const asset = poster || (selectedPhoto ? assetFor(selectedPhoto) : null);
    if (!asset) return;
    const download=document.getElementById('photo-download');
    const filename='yuanze-'+asset.src.split('/').pop();
    download.href=asset.src+'?download='+encodeURIComponent(filename);
    download.download=filename;download.hidden=false;
    download.textContent=language==='en'?'Download image':'下载图片';
    // A lightweight image appears first; a screen-sized preview then replaces it.
    // Full original artwork is requested only through the download control.
    if (photo.dataset.original !== asset.src) {
      const request = ++viewerRequest;
      photo.dataset.original = asset.src;
      photoError.hidden = true; photo.hidden = false; photo.src = previewURL(asset.src);
      const detailed = new window.Image();
      detailed.onload = () => {
        if (request === viewerRequest && photo.dataset.original === asset.src) photo.src = detailed.src;
      };
      // Keep the usable small image if the larger preview fails on a weak link.
      detailed.src = previewURL(asset.src, 1280);
    }
    photo.alt = poster ? poster.title[language] : content[language][`${selectedPhoto}Alt`] || content[language][`${selectedPhoto}Caption`];
    photoCaption.textContent = poster ? poster.title[language] : content[language][`${selectedPhoto}Caption`];
    dialog.setAttribute('aria-label', photoCaption.textContent);
    if (poster) {
      const visible = filteredPosters(), index = visible.findIndex(item => item.id === selectedPoster);
      posterPosition.textContent = format('posterPosition', {current:index + 1, total:visible.length});
      previousPoster.disabled = index <= 0;
      nextPoster.disabled = index >= visible.length - 1;
    }
  }

  function movePoster(step) {
    const visible = filteredPosters(), index = visible.findIndex(item => item.id === selectedPoster);
    const item = visible[index + step];
    if (selectedPoster && item) navigate(posterRoute(posterCategory, item.id), {replace:true, keepFocus:true, state:history.state});
  }

  function closeViewer() {
    if (!selectedPoster) { dialog.close(); return; }
    if (history.state?.yuanzePosterEntry) history.back();
    else navigate(posterRoute(), {replace:true, keepFocus:true});
  }

  function assetFor(id) {
    if (content.images[id]) return content.images[id];
    return content.certificates[id].versions[language];
  }

  function translate() {
    const copy = content[language];
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
    document.title = production ? copy.title : copy.previewTitle;
    document.querySelectorAll('[data-copy]').forEach(node => { node.textContent = copy[node.dataset.copy]; });
    document.querySelectorAll('[data-alt]').forEach(node => { node.alt = copy[node.dataset.alt]; });
    document.querySelectorAll('[data-aria]').forEach(node => { node.setAttribute('aria-label', copy[node.dataset.aria]); });
    document.querySelectorAll('[data-placeholder]').forEach(node => { node.placeholder = copy[node.dataset.placeholder]; });
    document.querySelectorAll('[data-page]').forEach(node => { node.setAttribute('aria-label',copy[node.dataset.page]); });
    frame.title = copy.catalogTab;
    document.querySelectorAll('[data-capability]').forEach(node => { node.textContent = copy.capabilities[Number(node.dataset.capability)]; });
    document.querySelectorAll('[data-certificate-image]').forEach(node => {
      const id = node.dataset.certificateImage;
      const asset = assetFor(id);
      node.src = previewURL(asset.src);
      node.alt = copy[`${id}Caption`];
      node.width = asset.width;
      node.height = asset.height;
    });
    document.querySelectorAll('[data-certificate-pdf]').forEach(node => { node.href = assetFor(node.dataset.certificatePdf).pdf; });
    document.querySelectorAll('[data-certificate-number]').forEach(node => { node.textContent = content.certificates[node.dataset.certificateNumber].number; });
    document.querySelectorAll('[data-certificate-date]').forEach(node => { node.textContent = `${copy.certificateExpiry} ${content.certificates[node.dataset.certificateDate].expiresAt}`; });
    renderPosters();
    renderBanner();
    updatePhoto();
    renderInquiry();
    renderSession();
    notifyLanguage();
  }

  function renderSession() {
    logout.disabled = loggingOut;
    logout.textContent = content[language][loggingOut ? 'loggingOut' : 'logout'];
    sessionMessage.hidden = !logoutFailed;
    sessionMessage.textContent = logoutFailed ? content[language].logoutError : '';
  }

  logout.addEventListener('click', async () => {
    if (!production || loggingOut) return;
    loggingOut = true; logoutFailed = false; renderSession();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    const options = {credentials:'same-origin', cache:'no-store', redirect:'error', signal:controller.signal, headers:{Accept:'application/json'}};
    try {
      // Obtain current CSRF at the moment of logout. Never store credentials in
      // the bundle, and do not automatically replay the POST after a timeout.
      const sessionResponse = await fetch('/api/session', options);
      if (sessionResponse.status === 401) { location.replace('/login'); return; }
      if (!sessionResponse.ok) throw Error('Session unavailable');
      const session = await sessionResponse.json();
      if (typeof session.csrf !== 'string' || !session.csrf) throw Error('Missing CSRF');
      const response = await fetch('/api/logout', {...options,method:'POST',headers:{...options.headers,'Content-Type':'application/json','X-CSRF-Token':session.csrf},body:'{}'});
      if (response.status === 401) { location.replace('/login'); return; }
      if (!response.ok || (await response.json()).ok !== true) throw Error('Logout unavailable');
      location.replace('/login');
    } catch (_) { logoutFailed = true; }
    finally { clearTimeout(timer); loggingOut = false; renderSession(); }
  });

  function setLanguage(value) {
    language = value;
    try { localStorage.setItem('yuanze-mobile-preview-language', language); localStorage.setItem('yuanze-language', language); } catch (_) {}
    translate();
  }
  toggle.addEventListener('click', () => setLanguage(language === 'zh' ? 'en' : 'zh'));
  document.getElementById('photo-language-toggle').addEventListener('click', () => setLanguage(language === 'zh' ? 'en' : 'zh'));
  frame.addEventListener('load', notifyLanguage);
  window.addEventListener('message', event => {
    if (!frame.hasAttribute('src') || event.origin !== location.origin || event.source !== frame.contentWindow || !event.data) return;
    if (event.data.type === 'yuanze-home') {navigate('home');return;}
    if (event.data.type === 'yuanze-auth-required') {location.replace('/login');return;}
    if (event.data.type === 'yuanze-language' && ['zh','en'].includes(event.data.language) && language !== event.data.language) setLanguage(event.data.language);
    if (event.data.type === 'yuanze-contact') navigate('contact');
    if (event.data.type === 'yuanze-shortlist' && Array.isArray(event.data.items)) {
      const seen = new Set();
      shortlist = event.data.items.filter(item => item && /^YZ-BC-\d{6,}$/.test(item.productCode) && !seen.has(item.productCode) && seen.add(item.productCode)).slice(0,100).map(item => ({productCode:item.productCode,capacity:typeof item.capacity === 'string' && /^\d+(?:\.\d+)?\s*(?:mL|ml|L|g|kg)$/.test(item.capacity) ? item.capacity : ''}));
      inquiryStatus = ''; renderInquiry();
    }
  });
  document.getElementById('copy-inquiry').addEventListener('click', async () => {
    const copy = content[language];
    const lines = [copy.inquiryTitle, ...shortlist.map(item => `${item.productCode} · ${item.capacity || '—'}`), document.getElementById('inquiry-note').value.trim()].filter(Boolean);
    try { await navigator.clipboard.writeText(lines.join('\n')); inquiryStatus = 'inquiryCopied'; }
    catch (_) { inquiryStatus = 'inquiryCopyFailed'; }
    renderInquiry();
  });
  document.querySelectorAll('[data-photo], [data-certificate]').forEach(button => button.addEventListener('click', () => {
    selectedPhoto = button.dataset.photo || button.dataset.certificate;
    selectedPoster = null;
    photoTrigger = button;
    updatePhoto();
    dialog.showModal();
    closePhoto.focus();
    scheduleBanner();
  }));
  closePhoto.addEventListener('click', closeViewer);
  dialog.addEventListener('cancel', event => { event.preventDefault(); closeViewer(); });
  dialog.addEventListener('keydown', event => {
    if (!selectedPoster || !['ArrowLeft','ArrowRight'].includes(event.key)) return;
    event.preventDefault(); movePoster(event.key === 'ArrowLeft' ? -1 : 1);
  });
  previousPoster.addEventListener('click', () => movePoster(-1));
  nextPoster.addEventListener('click', () => movePoster(1));
  photo.addEventListener('error', () => { photo.hidden = true; photoError.hidden = false; });
  dialog.addEventListener('close', () => {
    ++viewerRequest; photo.removeAttribute('src'); delete photo.dataset.original;
    selectedPhoto = null;
    selectedPoster = null;
    if (photoTrigger && !photoTrigger.closest('[hidden]')) photoTrigger.focus();
    scheduleBanner();
  });
  document.querySelectorAll('[data-page-link]').forEach(link => link.addEventListener('click', event => {
    event.preventDefault(); navigate(link.dataset.pageLink === 'products' ? posterRoute() : link.dataset.pageLink);
  }));
  document.querySelector('[data-copy="aboutLink"]').addEventListener('click', event => {event.preventDefault(); document.getElementById('about').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});});
  window.addEventListener('popstate', () => showPage(location.hash.slice(2), true));
  window.addEventListener('hashchange', () => showPage(location.hash.slice(2), true));

  initializePosters();
  initializeBanner();
  translate();
  showPage(location.hash.slice(2));
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('visible'); observer.unobserve(entry.target); }
    }), {threshold:0.08});
    document.querySelectorAll('.reveal').forEach(node => observer.observe(node));
    document.documentElement.classList.add('motion-ready');
  }
})();
