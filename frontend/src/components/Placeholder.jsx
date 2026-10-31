export default function Placeholder({ title, note }) {
  return (
    <div>
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="mt-2 text-stone-600">{note}</p>
    </div>
  )
}
