from typing import List, Tuple
import enum

import tqdm


class NLILabel(enum.Enum):
    NOT_MENTIONED = 0
    ENTAILMENT = 1
    CONTRADICTION = 2

    @classmethod
    def from_str(cls, s: str):
        if s == 'na':
            return cls.NOT_MENTIONED
        elif s == 'true':
            return cls.ENTAILMENT
        elif s == 'false':
            return cls.CONTRADICTION
        else:
            raise ValueError(f'Invalid input "{"s"}" to NLILabel.from_str.')


class ContractNLIExample:
    """
    A single training/test example for the contract NLI.

    Args:
        data_id: The example's unique identifier
        hypothesis_text: The hypothesis string
        context_text: The context string
        answer_text: The answer string
        start_position_character: The character position of the start of the answer
    """

    def __init__(
        self,
        data_id,
        hypothesis_text,
        hypothesis_tokens,
        context_text,
        tokens,
        splits,
        char_to_word_offset,
        label,
        annotated_spans,
    ):
        self.data_id: str = data_id
        self.hypothesis_text: str = hypothesis_text
        self.hypothesis_tokens: List[str] = hypothesis_tokens
        self.context_text: str = context_text
        self.tokens: List[str] = tokens
        # Note that splits are NOT unique
        self.splits: List[int] = splits
        self.char_to_word_offset: List[int] = char_to_word_offset
        self.label: NLILabel = label
        self.annotated_spans: List[int] = annotated_spans
        self.is_impossible: bool = label == NLILabel.NOT_MENTIONED

    @staticmethod
    def tokenize_and_align(text: str, spans: List[Tuple[int, int]]):
        """
        spans: Spans as character offsets. e.g. "world" in "Hello, world" will
            be represented as (7, 12).
        """
        # Split on whitespace so that different tokens may be attributed to their original position.
        tokens = []
        char_to_word_offset = []
        prev_is_whitespace = True
        splits = {si for s in spans for si in s}

        for i, c in enumerate(text):
            if c == ' ':
                # splits will be ignored on space
                prev_is_whitespace = True
            else:
                if prev_is_whitespace or i in splits:
                    tokens.append(c)
                else:
                    tokens[-1] += c
                prev_is_whitespace = False
            # len(tokens) == 0 when first characters are spaces
            char_to_word_offset.append(max(len(tokens) - 1, 0))

        splits = [char_to_word_offset[s[0]] for s in spans]
        return tokens, splits, char_to_word_offset

    @classmethod
    def load(cls, input_data) -> List['ContractNLIExample']:
        examples = []
        label_dict = {
            label_id: label_info['hypothesis']
            for label_id, label_info in input_data['labels'].items()}
        for document in tqdm.tqdm(input_data['documents']):
            if len(document['annotation_sets']) != 1:
                raise RuntimeError(
                    f'{len(document["annotation_sets"])} annotation sets given but '
                    'we only support single annotation set.')
            for label_id, annotation in document['annotation_sets'][0]['annotations'].items():
                data_id = f'{document["id"]}_{label_id}'
                context_text = document['text']
                hypothesis_text = label_dict[label_id]

                tokens, splits, char_to_word_offset = cls.tokenize_and_align(
                    context_text, document['spans'])
                hypothesis_tokens, _, _ = cls.tokenize_and_align(
                    hypothesis_text, [])

                example = cls(
                    data_id=data_id,
                    hypothesis_text=hypothesis_text,
                    hypothesis_tokens=hypothesis_tokens,
                    context_text=context_text,
                    tokens=tokens,
                    splits=splits,
                    char_to_word_offset=char_to_word_offset,
                    label=NLILabel.from_str(annotation['choice']),
                    annotated_spans=annotation['spans'],
                )
                examples.append(example)
        return examples