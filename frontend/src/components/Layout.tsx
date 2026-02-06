import React, { useState, useEffect } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import clsx from 'clsx';
import FeedbackModal from './FeedbackModal';
import { MindsetChecklist } from './MindsetChecklist';
import axios from 'axios';

interface LayoutProps {
  children?: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = () => {
  const [isDark, setIsDark] = useState(() => {
    return localStorage.getItem('theme') === 'dark' ||
      (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches);
  });
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);
  const [showChecklist, setShowChecklist] = useState(false);
  const location = useLocation();

  const saveMindsetNote = async (note: string) => {
    try {
        await axios.post('/journal/add', {
            entry_date: new Date().toISOString().split('T')[0],
            entry_time: new Date().toTimeString().split(' ')[0].slice(0, 5),
            symbol: "MINDSET", // Special tag
            strategy: "PRE-TRADE",
            sentiment: "Neutral",
            pnl: 0,
            notes: note
        });
        alert("Mindset Logged ✅");
    } catch (e) {
        console.error(e);
        alert("Failed to log mindset.");
    }
  };

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  const toggleTheme = () => setIsDark(!isDark);

  const navLinks = [
    { name: 'Home', path: '/' },
    { name: 'Dashboard', path: '/dashboard' },
    { name: 'Screener', path: '/screener' },
    { name: 'Backtest', path: '/backtest' },
    { name: 'Journal', path: '/journal' },
    { name: 'Audit', path: '/audit' },
    { name: 'Risk Map', path: '/portfolio-risk' },
    { name: 'Monte Carlo', path: '/monte-carlo' },
    { name: 'Docs', path: '/docs' },
  ];

  return (
    <div className="flex flex-col min-h-screen w-full bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 transition-colors duration-200">
      <nav id="navbar-main" className="fixed w-full z-20 top-0 start-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-screen-xl flex flex-wrap items-center justify-between mx-auto p-4">
          <Link to="/" id="nav-logo-link" className="flex items-center space-x-3 rtl:space-x-reverse group">
              <div className="flex items-center justify-center">
                 <img id="nav-logo-img" src="/static/img/logo.png" className="h-6 w-6 brightness-0 invert dark:invert-0" alt="Logo" />
              </div>
              <span className="self-center text-lg font-bold tracking-tight uppercase text-gray-900 dark:text-white">Trade<span className="text-primary-600 dark:text-primary-500">Guardian</span></span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-6">
            {navLinks.map((link) => (
              <Link
                key={link.path}
                to={link.path}
                id={`nav-link-${link.name.toLowerCase()}`}
                className={clsx(
                  "text-sm font-medium transition-colors hover:text-primary-600 dark:hover:text-primary-400",
                  location.pathname === link.path ? "text-primary-600 dark:text-primary-400" : "text-gray-600 dark:text-gray-400"
                )}
              >
                {link.name}
              </Link>
            ))}
          </div>

          <div className="flex md:order-2 space-x-3 items-center">
              <button
                  onClick={() => setShowChecklist(true)}
                  className="hidden md:flex items-center px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-700 rounded hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors mr-2"
              >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                  Pre-Flight
              </button>

              <button
                id="theme-toggle"
                type="button"
                onClick={toggleTheme}
                className="text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none rounded p-2 transition-all"
              >
                 {isDark ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"/><path d="M12 1v2"/><path d="M12 21v2"/><path d="M4.22 4.22l1.42 1.42"/><path d="M18.36 18.36l1.42 1.42"/><path d="M1 12h2"/><path d="M21 12h2"/><path d="M4.22 19.78l1.42-1.42"/><path d="M18.36 5.64l1.42-1.42"/></svg>
                 ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
                 )}
              </button>

              {/* Mobile menu button */}
              <button
                data-collapse-toggle="navbar-sticky"
                type="button"
                id="mobile-menu-toggle"
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="inline-flex items-center p-2 w-10 h-10 justify-center text-sm text-gray-500 rounded md:hidden hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-200 dark:text-gray-400 dark:hover:bg-gray-700 dark:focus:ring-gray-600"
                aria-controls="navbar-sticky"
                aria-expanded={isMobileMenuOpen}
              >
                  <span className="sr-only">Open main menu</span>
                  <svg className="w-5 h-5" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 17 14">
                      <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M1 1h15M1 7h15M1 13h15"/>
                  </svg>
              </button>
          </div>

          {/* Mobile Menu Dropdown */}
          <div className={clsx("items-center justify-between w-full md:hidden", isMobileMenuOpen ? "block" : "hidden")} id="navbar-sticky">
            <ul className="flex flex-col p-4 md:p-0 mt-4 font-medium border border-gray-100 rounded bg-gray-50 md:space-x-8 rtl:space-x-reverse md:flex-row md:mt-0 md:border-0 md:bg-white dark:bg-gray-800 md:dark:bg-gray-900 dark:border-gray-700">
              {navLinks.map((link) => (
                <li key={link.path}>
                   <Link
                    to={link.path}
                    id={`mobile-nav-link-${link.name.toLowerCase()}`}
                    className={clsx(
                      "block py-2 px-3 rounded hover:bg-gray-100 md:hover:bg-transparent md:hover:text-primary-700 md:p-0 md:dark:hover:text-primary-500 dark:hover:bg-gray-700 dark:hover:text-white md:dark:hover:bg-transparent dark:border-gray-700",
                       location.pathname === link.path ? "text-primary-700 dark:text-white" : "text-gray-900 dark:text-white"
                    )}
                    onClick={() => setIsMobileMenuOpen(false)}
                   >
                     {link.name}
                   </Link>
                </li>
              ))}
              <li>
                  <button
                      onClick={() => {
                          setShowChecklist(true);
                          setIsMobileMenuOpen(false);
                      }}
                      className="block w-full text-left py-2 px-3 rounded hover:bg-gray-100 md:hover:bg-transparent md:hover:text-primary-700 md:p-0 md:dark:hover:text-primary-500 dark:hover:bg-gray-700 dark:text-white md:dark:hover:bg-transparent dark:border-gray-700 text-gray-900"
                  >
                      Pre-Flight
                  </button>
              </li>
            </ul>
          </div>
        </div>
      </nav>

      <div className="h-20"></div>

      <main className="container mx-auto px-4 flex-grow py-6 max-w-7xl animate-fade-in">
         <Outlet />
      </main>

      <footer className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 mt-auto">
        <div className="w-full mx-auto max-w-screen-xl p-6 md:flex md:items-center md:justify-between">
          <span className="text-sm text-gray-500 sm:text-center dark:text-gray-400">© 2025 <Link to="/" className="hover:underline">TradeGuardian</Link>.</span>
          <ul className="flex flex-wrap items-center mt-3 text-sm font-medium text-gray-500 dark:text-gray-400 sm:mt-0 space-x-4 md:space-x-6">
            <li><a href="https://github.com/Ramkumar78/OptionThetaRisk" target="_blank" rel="noopener noreferrer" className="hover:text-primary-600 transition-colors">GitHub</a></li>
            <li>
                <button
                    id="footer-feedback-btn"
                    onClick={() => setIsFeedbackOpen(true)}
                    className="hover:text-primary-600 transition-colors focus:outline-none"
                >
                    Feedback
                </button>
            </li>
          </ul>
        </div>
        <div className="text-center pb-6 text-xs text-gray-400 dark:text-gray-500 max-w-2xl mx-auto px-4">
            Disclaimer: This application is for educational and informational purposes only.
            It does not constitute financial advice. Trading options involves significant risk
            and is not suitable for all investors. Data provided by third-party sources may be delayed or inaccurate.
        </div>
      </footer>

      <FeedbackModal isOpen={isFeedbackOpen} onClose={() => setIsFeedbackOpen(false)} />
      <MindsetChecklist
        isOpen={showChecklist}
        onClose={() => setShowChecklist(false)}
        onConfirm={() => {
            saveMindsetNote("Completed Pre-Flight Checklist: All Systems Go.");
            setShowChecklist(false);
        }}
        actionName="Complete Check"
      />
    </div>
  );
};

export default Layout;
