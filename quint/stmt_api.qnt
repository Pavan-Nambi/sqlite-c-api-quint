module SqliteStmtApi {
  type Scenario = str

  val BindResetRetains: Scenario = "bind_reset_retains"
  val ClearBindingsNull: Scenario = "clear_bindings_null"
  val BindAfterStepMisuse: Scenario = "bind_after_step_misuse"
  val DataCountRowDone: Scenario = "data_count_row_done"
  val BlobZeroLengthNull: Scenario = "column_blob_zero_length_null"

  type ModelState = {
    scenario: Scenario,
    stage: int,
    bindingsSet: bool,
    resetCalled: bool,
    clearCalled: bool,
    firstStepRow: bool,
    secondStepRow: bool,
    misuseObserved: bool,
    dataCountBeforeZero: bool,
    dataCountRowNonZero: bool,
    dataCountDoneZero: bool,
    blobZeroIsNull: bool,
  }

  var state: ModelState

  val Scenarios: Set[Scenario] = Set(
    BindResetRetains,
    ClearBindingsNull,
    BindAfterStepMisuse,
    DataCountRowDone,
    BlobZeroLengthNull
  )

  def fresh(scenario: Scenario): ModelState = {
    scenario: scenario,
    stage: 0,
    bindingsSet: false,
    resetCalled: false,
    clearCalled: false,
    firstStepRow: false,
    secondStepRow: false,
    misuseObserved: false,
    dataCountBeforeZero: false,
    dataCountRowNonZero: false,
    dataCountDoneZero: false,
    blobZeroIsNull: false,
  }

  def nextState(
    current: ModelState,
    stage: int,
    bindingsSet: bool,
    resetCalled: bool,
    clearCalled: bool,
    firstStepRow: bool,
    secondStepRow: bool,
    misuseObserved: bool,
    dataCountBeforeZero: bool,
    dataCountRowNonZero: bool,
    dataCountDoneZero: bool,
    blobZeroIsNull: bool,
  ): ModelState = {
    scenario: current.scenario,
    stage: stage,
    bindingsSet: bindingsSet,
    resetCalled: resetCalled,
    clearCalled: clearCalled,
    firstStepRow: firstStepRow,
    secondStepRow: secondStepRow,
    misuseObserved: misuseObserved,
    dataCountBeforeZero: dataCountBeforeZero,
    dataCountRowNonZero: dataCountRowNonZero,
    dataCountDoneZero: dataCountDoneZero,
    blobZeroIsNull: blobZeroIsNull,
  }

  action initDoc = {
    nondet scenario = Scenarios.oneOf()
    state' = fresh(scenario)
  }

  action init = initDoc

  action bindValuesForRetain = all {
    state.scenario == BindResetRetains,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      true,
      state.resetCalled,
      state.clearCalled,
      state.firstStepRow,
      state.secondStepRow,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action firstRowWithRetainedBindings = all {
    state.scenario == BindResetRetains,
    state.stage == 1,
    state.bindingsSet,
    state' = nextState(
      state,
      2,
      state.bindingsSet,
      state.resetCalled,
      state.clearCalled,
      true,
      state.secondStepRow,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action resetRetainedStatement = all {
    state.scenario == BindResetRetains,
    state.stage == 2,
    state.firstStepRow,
    state' = nextState(
      state,
      3,
      state.bindingsSet,
      true,
      state.clearCalled,
      state.firstStepRow,
      state.secondStepRow,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action secondRowWithRetainedBindings = all {
    state.scenario == BindResetRetains,
    state.stage == 3,
    state.bindingsSet,
    state.resetCalled,
    state' = nextState(
      state,
      4,
      state.bindingsSet,
      state.resetCalled,
      state.clearCalled,
      state.firstStepRow,
      true,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action bindValuesForClear = all {
    state.scenario == ClearBindingsNull,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      true,
      state.resetCalled,
      state.clearCalled,
      state.firstStepRow,
      state.secondStepRow,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action firstRowBeforeClear = all {
    state.scenario == ClearBindingsNull,
    state.stage == 1,
    state.bindingsSet,
    state' = nextState(
      state,
      2,
      state.bindingsSet,
      state.resetCalled,
      state.clearCalled,
      true,
      state.secondStepRow,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action resetBeforeClear = all {
    state.scenario == ClearBindingsNull,
    state.stage == 2,
    state.firstStepRow,
    state' = nextState(
      state,
      3,
      state.bindingsSet,
      true,
      state.clearCalled,
      state.firstStepRow,
      state.secondStepRow,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action clearAllBindings = all {
    state.scenario == ClearBindingsNull,
    state.stage == 3,
    state.bindingsSet,
    state.resetCalled,
    state' = nextState(
      state,
      4,
      false,
      state.resetCalled,
      true,
      state.firstStepRow,
      state.secondStepRow,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action secondRowAfterClear = all {
    state.scenario == ClearBindingsNull,
    state.stage == 4,
    state.clearCalled,
    not(state.bindingsSet),
    state' = nextState(
      state,
      5,
      state.bindingsSet,
      state.resetCalled,
      state.clearCalled,
      state.firstStepRow,
      true,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action firstRowBeforeBindMisuse = all {
    state.scenario == BindAfterStepMisuse,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.bindingsSet,
      state.resetCalled,
      state.clearCalled,
      true,
      state.secondStepRow,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action bindDuringActiveRowMisuse = all {
    state.scenario == BindAfterStepMisuse,
    state.stage == 1,
    state.firstStepRow,
    state' = nextState(
      state,
      2,
      state.bindingsSet,
      state.resetCalled,
      state.clearCalled,
      state.firstStepRow,
      state.secondStepRow,
      true,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action observeDataCountBeforeStep = all {
    state.scenario == DataCountRowDone,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.bindingsSet,
      state.resetCalled,
      state.clearCalled,
      state.firstStepRow,
      state.secondStepRow,
      state.misuseObserved,
      true,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action observeDataCountAtFirstRow = all {
    state.scenario == DataCountRowDone,
    state.stage == 1,
    state.dataCountBeforeZero,
    state' = nextState(
      state,
      2,
      state.bindingsSet,
      state.resetCalled,
      state.clearCalled,
      true,
      state.secondStepRow,
      state.misuseObserved,
      state.dataCountBeforeZero,
      true,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action observeDataCountAtSecondRow = all {
    state.scenario == DataCountRowDone,
    state.stage == 2,
    state.dataCountRowNonZero,
    state' = nextState(
      state,
      3,
      state.bindingsSet,
      state.resetCalled,
      state.clearCalled,
      state.firstStepRow,
      true,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action observeDataCountAtDone = all {
    state.scenario == DataCountRowDone,
    state.stage == 3,
    state.dataCountRowNonZero,
    state' = nextState(
      state,
      4,
      state.bindingsSet,
      state.resetCalled,
      state.clearCalled,
      state.firstStepRow,
      state.secondStepRow,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      true,
      state.blobZeroIsNull
    ),
  }

  action stepBlobZeroLengthRow = all {
    state.scenario == BlobZeroLengthNull,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.bindingsSet,
      state.resetCalled,
      state.clearCalled,
      true,
      state.secondStepRow,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      state.blobZeroIsNull
    ),
  }

  action observeBlobZeroLengthAsNull = all {
    state.scenario == BlobZeroLengthNull,
    state.stage == 1,
    state.firstStepRow,
    state' = nextState(
      state,
      2,
      state.bindingsSet,
      state.resetCalled,
      state.clearCalled,
      state.firstStepRow,
      state.secondStepRow,
      state.misuseObserved,
      state.dataCountBeforeZero,
      state.dataCountRowNonZero,
      state.dataCountDoneZero,
      true
    ),
  }

  action step = any {
    bindValuesForRetain,
    firstRowWithRetainedBindings,
    resetRetainedStatement,
    secondRowWithRetainedBindings,

    bindValuesForClear,
    firstRowBeforeClear,
    resetBeforeClear,
    clearAllBindings,
    secondRowAfterClear,

    firstRowBeforeBindMisuse,
    bindDuringActiveRowMisuse,

    observeDataCountBeforeStep,
    observeDataCountAtFirstRow,
    observeDataCountAtSecondRow,
    observeDataCountAtDone,

    stepBlobZeroLengthRow,
    observeBlobZeroLengthAsNull,
  }

  val stmtBindResetRetainsPath =
    (state.scenario == BindResetRetains) implies (
      state.stage <= 4
      and ((state.stage >= 1) implies state.bindingsSet)
      and ((state.stage >= 2) implies state.firstStepRow)
      and ((state.stage >= 3) implies state.resetCalled)
      and ((state.stage >= 4) implies state.secondStepRow)
    )

  val stmtClearBindingsNullPath =
    (state.scenario == ClearBindingsNull) implies (
      state.stage <= 5
      and ((state.stage >= 1 and state.stage <= 3) implies state.bindingsSet)
      and ((state.stage >= 2) implies state.firstStepRow)
      and ((state.stage >= 3) implies state.resetCalled)
      and ((state.stage >= 4) implies (not(state.bindingsSet) and state.clearCalled))
      and ((state.stage >= 5) implies state.secondStepRow)
    )

  val stmtBindAfterStepMisusePath =
    (state.scenario == BindAfterStepMisuse) implies (
      state.stage <= 2
      and ((state.stage >= 1) implies state.firstStepRow)
      and ((state.stage >= 2) implies state.misuseObserved)
    )

  val stmtDataCountRowDonePath =
    (state.scenario == DataCountRowDone) implies (
      state.stage <= 4
      and ((state.stage >= 1) implies state.dataCountBeforeZero)
      and ((state.stage >= 2) implies (state.firstStepRow and state.dataCountRowNonZero))
      and ((state.stage >= 3) implies state.secondStepRow)
      and ((state.stage >= 4) implies state.dataCountDoneZero)
    )

  val stmtBlobZeroLengthNullPath =
    (state.scenario == BlobZeroLengthNull) implies (
      state.stage <= 2
      and ((state.stage >= 1) implies state.firstStepRow)
      and ((state.stage >= 2) implies state.blobZeroIsNull)
    )
}
