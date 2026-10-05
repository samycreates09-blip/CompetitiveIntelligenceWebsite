type PageHeaderProps = {
  eyebrow: string;
  title: string;
  note?: string;
};

export function PageHeader({ eyebrow, title, note }: PageHeaderProps) {
  return (
    <section className="page-header-row">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {note ? <div className="page-note">{note}</div> : null}
    </section>
  );
}