import { SelectedStudyWorkbench } from "@/components/shell/SelectedStudyWorkbench";
import { StudyProvider } from "@/components/shell/StudyContext";
import { normalizeStudyId } from "@/components/shell/studyId";

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

// The shell loads the selected study (?study=<id>) or the seeded synthetic
// study. Lane A (#26) drives selection after upload via useStudySelection().
export default async function Home({ searchParams }: Props) {
  const params = await searchParams;
  return (
    <StudyProvider initialStudyId={normalizeStudyId(params.study)}>
      <SelectedStudyWorkbench />
    </StudyProvider>
  );
}
