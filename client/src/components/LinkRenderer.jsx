export const LinkRenderer = (props) => {
  return (
    <a
      {...props}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-500 underline">
    </a>
  );
}
