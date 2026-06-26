import LiveMap from './components/LiveMap';

export default function Home() {
  return (
    <main style={{ position: 'fixed', inset: 0 }}>
      <LiveMap />
    </main>
  );
}
