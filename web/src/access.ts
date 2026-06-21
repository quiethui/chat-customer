/**
 * @see https://umijs.org/docs/max/access#access
 * */
export default function access(
  initialState: { currentUser?: API.CurrentUser } | undefined,
) {
  const { currentUser } = initialState ?? {};
  return {
    canAccess: !!currentUser,
    canAdmin: currentUser && currentUser.access === 'admin',
    canAgent: !!currentUser,
  };
}
