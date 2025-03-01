import { Resolution } from "@/types/post";

export enum QuestionType {
  Numeric = "numeric",
  Date = "date",
  Binary = "binary",
  MultipleChoice = "multiple_choice",
}

export enum QuestionOrder {
  ActivityDesc = "-activity",
  WeeklyMovementDesc = "-weekly_movement",
  PublishTimeDesc = "-published_at",
  LastPredictionTimeAsc = "user_last_forecasts_date",
  LastPredictionTimeDesc = "-user_last_forecasts_date",
  DivergenceAsc = "divergence",
  VotesDesc = "-vote_score",
  CommentCountDesc = "-comment_count",
  UnreadCommentCountDesc = "-unread_comment_count",
  PredictionCountDesc = "-forecasts_count",
  CloseTimeAsc = "scheduled_close_time",
  ScoreDesc = "-score",
  ScoreAsc = "score",
  ResolveTimeAsc = "scheduled_resolve_time",
  HotDesc = "-hotness",
  HotAsc = "hotness",
  RankDesc = "-rank",
}

export type Scaling = {
  range_max: number | null;
  range_min: number | null;
  zero_point: number | null;
};

export enum AggregationMethod {
  RecencyWeighted = "recency_weighted",
  Unweighted = "unweighted",
  SingleAggregation = "single_aggregation",
}

export type Bounds = {
  belowLower: number;
  aboveUpper: number;
};

export type Quartiles = {
  median: number;
  lower25: number;
  upper75: number;
};

export type ExtendedQuartiles = Quartiles & {
  lower10: number;
  upper90: number;
};

export type Forecast = {
  question_id: number;
  start_time: number;
  end_time: number | null;
  forecast_values: number[];
  interval_lower_bounds: number[] | null;
  centers: number[] | null;
  interval_upper_bounds: number[] | null;
};

export type UserForecast = Forecast & {
  slider_values: any | null; // TODO: solidify this
};

export type UserForecastHistory = {
  history: UserForecast[];
  latest?: UserForecast;
};

export type AggregateForecast = Forecast & {
  method: AggregationMethod;
  forecaster_count: number;
  means: number[] | null;
  histogram: number[] | null;
};

export type AggregateForecastHistory = {
  history: AggregateForecast[];
  latest?: AggregateForecast;
};

export type Aggregations = {
  recency_weighted: AggregateForecastHistory;
  unweighted?: AggregateForecastHistory;
  single_aggregation?: AggregateForecastHistory;
};

export type BaseForecast = {
  timestamps: number[];
  nr_forecasters: number[];
  my_forecasts: {
    timestamps: number[];
    medians: number[];
    slider_values: any | null;
  } | null;
};

export type NumericForecast = BaseForecast & {
  medians: number[];
  q3s: number[];
  q1s: number[];
  means: number[];
  latest_pmf: number[];
  latest_cdf: number[];
  histogram?: number[];
};

export type MultipleChoiceForecast = BaseForecast & {
  [value_choice_n: string]: Array<{
    median: number;
    q3: number;
    q1: number;
  }>;
};

export type Question = {
  id: number;
  title: string;
  description: string;
  created_at: string;
  updated_at: string;
  open_time?: string;
  scheduled_resolve_time: string;
  actual_resolve_time?: string;
  resolution_set_time?: string;
  scheduled_close_time: string;
  actual_close_time?: string;
  forecast_scoring_ends?: string;
  type: QuestionType;
  options?: string[];
  scaling: Scaling;
  possibilities: {
    format?: string;
    high?: string;
    low?: string;
    type?: string;
    scale?: {
      max: number;
      min: number;
      deriv_ratio: number;
    };
  }; // TODO: update type
  resolution: Resolution | null;
  fine_print: string | null;
  resolution_criteria: string | null;
  label: string | null;
  nr_forecasters: number;
  author_username: string;
  post_id?: number;
  display_divergences?: number[][];
  aggregations: Aggregations;
  my_forecasts?: UserForecastHistory;
};

export type QuestionWithNumericForecasts = Question & {
  type: QuestionType.Numeric | QuestionType.Date | QuestionType.Binary;
  forecasts: NumericForecast;
  open_lower_bound?: boolean;
  open_upper_bound?: boolean;
};
export type QuestionWithMultipleChoiceForecasts = Question & {
  type: QuestionType.MultipleChoice;
  forecasts: MultipleChoiceForecast;
};

export type QuestionWithForecasts =
  | QuestionWithNumericForecasts
  | QuestionWithMultipleChoiceForecasts;

export type ForecastData = {
  continuousCdf: number[] | null;
  probabilityYes: number | null;
  probabilityYesPerCategory: Record<string, number> | null;
};
