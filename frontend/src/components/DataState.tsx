type DataStateProps = {
  status: 'loading' | 'error' | 'empty';
  message: string;
  detail?: string;
};

export function DataState({ status, message, detail }: DataStateProps) {
  return (
    <div className="data-state" data-status={status}>
      <strong>{message}</strong>
      {detail ? <span>{detail}</span> : null}
    </div>
  );
}
