import { redirect } from 'next/navigation';

export default function Home() {
  // Redirect to opportunities page as the main landing
  redirect('/opportunities');
}
