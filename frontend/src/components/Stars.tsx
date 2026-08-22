interface StarsProps {
  value: number | null;
  editable?: boolean;
  onChange?: (n: number) => void;
}

export function Stars({ value, editable, onChange }: StarsProps) {
  return (
    <span className="stars">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          className={`star ${value && n <= value ? "filled" : ""} ${editable ? "" : "readonly"}`}
          disabled={!editable}
          onClick={() => editable && onChange?.(n)}
        >
          {value && n <= value ? "★" : "☆"}
        </button>
      ))}
    </span>
  );
}
