import { useNavigate } from 'react-router-dom'
import HeroSection from './HeroSection'
import HowItWorksSection from './HowItWorksSection'
import FeaturesSection from './FeaturesSection'
import StockCheckSection from './StockCheckSection'
import PromiseSection from './PromiseSection'
import CtaBand from './CtaBand'

export default function LandingPage() {
  const navigate = useNavigate()
  return (
    <>
      <HeroSection onApply={() => navigate('/apply')} />
      <HowItWorksSection />
      <FeaturesSection />
      <StockCheckSection />
      <PromiseSection />
      <CtaBand />
    </>
  )
}
