import type { Workspace } from "../lib/types";

// DEMO ONLY (HELIX_DEMO_UNQUALIFIED_PACKAGES). The backend lists the section packages that
// run without a passing qualification; every place that shows one must carry this label.
export const DEMO_NOT_QUALIFIED = "Demo: not qualified";

type DemoPackage = NonNullable<Workspace["demo_unqualified_packages"]>[number];

export function demoPackages(workspace: Workspace): DemoPackage[] {
  return workspace.demo_unqualified_packages ?? [];
}

export function demoPackageFor(
  workspace: Workspace,
  match: { sectionPackageId?: string; prototypeSectionId?: string },
): DemoPackage | undefined {
  return demoPackages(workspace).find(
    (item) =>
      (match.sectionPackageId !== undefined && item.section_package_id === match.sectionPackageId) ||
      (match.prototypeSectionId !== undefined && item.prototype_section_id === match.prototypeSectionId),
  );
}

export function DemoLabel({ item, context }: { item: DemoPackage | undefined; context: string }) {
  if (!item) {
    return null;
  }
  return (
    <span
      className="demo-label"
      data-testid={`demo-label-${context}-${item.section_package_id}`}
      title="Demo only. This section package has not passed qualification (qualification_status pending)."
    >
      {item.label}
    </span>
  );
}

export function DemoBanner({ workspace }: { workspace: Workspace }) {
  const items = demoPackages(workspace);
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="demo-banner" role="note" data-testid="demo-mode-banner">
      <strong>{DEMO_NOT_QUALIFIED}</strong>
      <span>
        Demo only, not qualification: {items.map((item) => item.title).join(" and ")} run with
        qualification_status pending.
      </span>
    </div>
  );
}
