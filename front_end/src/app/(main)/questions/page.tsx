import { Suspense } from "react";

import AwaitedPostsFeed from "@/components/posts_feed";
import LoadingIndicator from "@/components/ui/loading_indicator";
import ProjectsApi from "@/services/projects";
import { SearchParams } from "@/types/navigation";
import { QuestionOrder } from "@/types/question";

import FeedFilters from "./components/feed_filters";
import QuestionTopics from "./components/question_topics";
import { generateFiltersFromSearchParams } from "./helpers/filters";

export default async function Questions({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const filters = generateFiltersFromSearchParams(
    searchParams,
    // Default Feed ordering should be hotness
    QuestionOrder.HotDesc
  );
  const topics = await ProjectsApi.getTopics();

  return (
    <main className="mx-auto mt-4 min-h-min w-full max-w-5xl flex-auto px-0 sm:px-2 md:px-3">
      <div className="gap-3 p-0 sm:flex sm:flex-row sm:gap-4">
        <QuestionTopics topics={topics} />
        <div className="min-h-[calc(100vh-300px)] grow overflow-x-hidden p-2 pt-2.5 no-scrollbar sm:p-0 sm:pt-5">
          <FeedFilters />
          <Suspense
            key={JSON.stringify(searchParams)}
            fallback={
              <LoadingIndicator className="mx-auto h-8 w-24 text-gray-600 dark:text-gray-600-dark" />
            }
          >
            <AwaitedPostsFeed filters={filters} />
          </Suspense>
        </div>
      </div>
    </main>
  );
}
