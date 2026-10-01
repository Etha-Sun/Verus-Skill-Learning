### Meeting

SkillOpt

```
  Current Skill
      ↓
  Run 40 Training Tasks
      ↓
  Separate Successful and Failed Trajectories
      ↓
  Split Each Pool into Minibatches (≤8 traces)
      ↓
  Analyze Each Minibatch with the Same Current Skill
      • Failures: identify common problems and missing guidance
      • Successes: extract reusable strategies
      • Propose up to 4 skill edits per minibatch
      ↓
  Merge Failure Proposals / Merge Success Proposals
      ↓
  Combine, Deduplicate, and Resolve Conflicts
      ↓
  Select Top-L Edits (L = current learning-rate budget)
      ↓
  Apply Edits → Candidate Skill
      ↓
  Validation Gate
      • Improved → accept candidate
      • Otherwise → retain current skill
```

Method

```
  Run Training Tasks with the Initial Skill 
      ↓
  Analyze Traces for Stagnation and Regression
      • Stagnation / Regression
      ↓
  Select Representative States and Failure Patterns
      ↓
  Generate Alternative Experiences
      • Hint / Obfs
      ↓
  Group Related Experiences by Source Task
      ↓
  SkillOpt Reflection
      • Diagnose the original obstacle
      • Compare successful and failed strategies
      • Identify transferable actions and applicability boundaries
      ↓
  Propose Skill Cards
      Trigger / Action / Why / Validate / Avoid When
      ↓
  Merge, Deduplicate, Select, and Validate
      ↓
  Freeze the Skill / Card Bank
```



40 problems -> 160 obfuscated
40 traces -> 160 augment

- card / plain skill
- grouping: random / positive-negative / problem grouped
- Data: original / augmented / obfuscated
- Augment: random point / selected point

|      | Data                                        | Analysis Grouping            |                      |
| ---- | ------------------------------------------- | ---------------------------- | -------------------- |
| A    | Random 40 train cases                       | (Positive/Negative) / Random | Cards / Single Skill |
| B    | Random 10 train cases                       | (Positive/Negative) / Random | Cards / Single Skill |
| C    | Augment data 160                            | Problem Grouped              | Cards                |
| D    | Augment 40 problems (stagnation/regression) | Problem Grouped / Random     | Cards / Single Skill |
| E    | Obfs 160 cases                              | Problem Grouped              | Cards                |
| F    | Obfs 40 cases                               | Problem Grouped              | Cards / Single Skill |
| G    | Augment 40 problems (random point)          | Problem Grouped              | Cards                |

![image-20260930225246826](/Users/sun/Library/Application Support/typora-user-images/image-20260930225246826.png)