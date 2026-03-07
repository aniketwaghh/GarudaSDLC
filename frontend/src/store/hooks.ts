import { useDispatch, useSelector } from "react-redux";
import type { RootState, AppDispatch } from "./index";

// Export pre-typed hooks
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector = (selector: (state: RootState) => any) =>
  useSelector(selector);
