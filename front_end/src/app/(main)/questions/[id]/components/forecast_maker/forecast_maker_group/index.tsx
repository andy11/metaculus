import { useTranslations } from "next-intl";
import { FC } from "react";

import { PostWithForecasts } from "@/types/post";
import {
  QuestionType,
  QuestionWithForecasts,
  QuestionWithNumericForecasts,
} from "@/types/question";
import { sortGroupPredictionOptions } from "@/utils/questions";

import ForecastMakerGroupBinary from "./forecast_maker_group_binary";
import ForecastMakerGroupContinuous from "./forecast_maker_group_continuous";
import ForecastMakerContainer from "../container";

type Props = {
  resolutionCriteria: string | null;
  finePrint: string;
  questions: QuestionWithForecasts[];
  post: PostWithForecasts;
  canPredict: boolean;
  canResolve: boolean;
};

const ForecastMakerGroup: FC<Props> = ({
  post,
  resolutionCriteria,
  finePrint,
  questions,
  canResolve,
  canPredict,
}) => {
  const t = useTranslations();

  const renderForecastMaker = () => {
    const tileType = questions.at(0)?.type;

    if (!tileType) {
      return null;
    }

    switch (tileType) {
      case QuestionType.Binary:
        const sortedQuestions = sortGroupPredictionOptions(
          questions as QuestionWithNumericForecasts[]
        );
        return (
          <ForecastMakerGroupBinary
            post={post}
            questions={sortedQuestions}
            canResolve={canResolve}
            canPredict={canPredict}
          />
        );
      case QuestionType.Numeric:
      case QuestionType.Date:
        return (
          <ForecastMakerGroupContinuous
            post={post}
            questions={questions as QuestionWithNumericForecasts[]}
            canResolve={canResolve}
            canPredict={canPredict}
          />
        );
      default:
        return null;
    }
  };

  return (
    <ForecastMakerContainer
      title={t("MakePrediction")}
      resolutionCriteria={[
        {
          title: t("resolutionCriteria"),
          content: resolutionCriteria,
          finePrint,
        },
      ]}
    >
      {renderForecastMaker()}
    </ForecastMakerContainer>
  );
};

export default ForecastMakerGroup;
