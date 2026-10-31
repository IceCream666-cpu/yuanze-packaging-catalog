import React from 'react';
import {createRoot} from 'react-dom/client';
import Portfolio from './Portfolio.jsx';
import './portfolio.css';

window.gsap.registerPlugin(window.ScrollTrigger);
createRoot(document.getElementById('root')).render(<Portfolio />);
