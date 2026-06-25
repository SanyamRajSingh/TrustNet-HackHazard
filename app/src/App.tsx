import { Route, Routes } from 'react-router';
import { Toaster } from '@/components/ui/sonner';
import Layout from './components/Layout';
import AboutPage from './pages/AboutPage';
import CommunityPage from './pages/CommunityPage';
import EntityPage from './pages/EntityPage';
import HomePage from './pages/HomePage';
import ResultPage from './pages/ResultPage';

function App() {
  return (
    <>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/result/:id" element={<ResultPage />} />
          <Route path="/entity/:hash" element={<EntityPage />} />
          <Route path="/community" element={<CommunityPage />} />
          <Route path="/about" element={<AboutPage />} />
        </Route>
      </Routes>
      <Toaster position="top-center" richColors />
    </>
  );
}

export default App;