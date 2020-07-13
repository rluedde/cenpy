#############
# UTILITIES #
#############


def _fuzzy_match(matchtarget, matchlist, return_table=False):
    """
    Conduct a fuzzy match with matchtarget, within the list of possible match candidates in matchlist. 

    Parameters
    ---------
    matchtarget :   str
                 a string to be matched to a set of possible candidates
    matchlist   :   list of str
                 a list (or iterable) containing strings we are interested in matching
    return_table:   bool
                 whether to return the full table of scored candidates, or to return only the single
                 best match. If False (the default), only the best match is returned.
    
    Notes
    -----
    consult the docstring for Product.check_match for more information on how the actual matching
    algorithm works. 
    """
    split = matchtarget.split(",")
    if len(split) == 2:
        target, state = split
    elif len(split) == 1:
        target = split[0]
    else:
        raise AssertionError(
            "Uncertain place identifier {}. The place identifier should "
            'look something like "placename, state" or, for larger areas, '
            "like Combined Statistical Areas or Metropolitan Statistical Areas,"
            "placename1-placename2, state1-state2-state3".format(target)
        )

    table = pandas.DataFrame({"target": matchlist})
    table["score"] = table.target.apply(
        lambda x: fuzz.partial_ratio(target.strip().lower(), x.lower())
    )
    if len(split) == 1:
        if (table.score == table.score.max()).sum() > 1:
            ixmax, rowmax = _break_ties(matchtarget, table)
        else:
            ixmax = table.score.idxmax()
            rowmax = table.loc[ixmax]
        if return_table:
            return rowmax, table.sort_values("score")
        return rowmax

    in_state = table.target.str.lower().str.endswith(state.strip().lower())

    assert any(in_state), (
        "State {} is not found from place {}. "
        "Should be a standard Census abbreviation, like"
        " CA, AZ, NC, or PR".format(state, matchtarget)
    )
    table = table[in_state]
    if (table.score == table.score.max()).sum() > 1:
        ixmax, rowmax = _break_ties(matchtarget, table)
    else:
        ixmax = table.score.idxmax()
        rowmax = table.loc[ixmax]
    if return_table:
        return rowmax, table.sort_values("score")
    return rowmax


def _coerce(column, kind):
    """
    Converty type of column to kind, or keep column unchanged
    if that conversion fails.
    """
    try:
        return column.astype(kind)
    except ValueError:
        return column


def _replace_missing(column):

    """
    replace ACS missing values using numpy.nan. 
    """

    _ACS_MISSING = (-999999999, -888888888, -666666666, -555555555, -333333333, -222222222)

    for val in _ACS_MISSING:
        column.replace(val, numpy.nan, inplace=True)
    return column


def _break_ties(matchtarget, table):
    """
    break ties in the fuzzy matching algorithm using a second scoring method 
    which prioritizes full string matches over substring matches.  
    """
    split = matchtarget.split(",")
    if len(split) == 2:
        target, state = split
    else:
        target = split[0]
    table["score2"] = table.target.apply(
        lambda x: fuzz.ratio(target.strip().lower(), x.lower())
    )
    among_winners = table[table.score == table.score.max()]
    double_winners = among_winners[among_winners.score2 == among_winners.score2.max()]
    if double_winners.shape[0] > 1:
        ixmax = double_winners.score2.idxmax()
        ixmax_row = double_winners.loc[ixmax]
        warn(
            "Cannot disambiguate placename {}. Picking the shortest, best "
            "matched placename, {}, from {}".format(
                matchtarget, ixmax_row.target, ", ".join(double_winners.target.tolist())
            )
        )
        return ixmax, ixmax_row
    ixmax = double_winners.score2.idxmax()
    return ixmax, double_winners.loc[ixmax]


def _can_int(char):
    """check if a character can be turned into an integer"""
    try:
        int(char)
        return True
    except ValueError:
        return False
