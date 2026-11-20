import Sheet from '../../components/ui/Sheet'
import DotList from '../../components/ui/DotList'

export default function MissedChancesCard() {
  return (
    <Sheet as="article">
      <h3>What it costs in missed chances</h3>
      <p className="note">Money the shop could have put to work.</p>
      <DotList
        items={[
          'Cannot stock up before a festival, when sales are highest.',
          'Cannot buy in bulk from suppliers.',
          'Shelving, a fridge or a new product line stay on hold.',
        ]}
      />
      <p className="note foot">
        Small businesses go without about ₹30 lakh crore of credit, roughly 24% of what they ask
        for. For women-owned shops the gap is 35%.{' '}
        <em>Source: SIDBI and Crisil MSME Pulse, 2025.</em>
      </p>
    </Sheet>
  )
}
