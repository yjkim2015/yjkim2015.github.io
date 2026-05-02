---
title: "Spring Batch 완전 가이드 — Chunk vs Tasklet"
categories:
- BATCH
toc: true
toc_sticky: true
toc_label: 목차
---

## 1. 비유 — 공장 생산 라인

배치(Batch) 처리는 공장 생산 라인과 같습니다. 수백만 개의 제품을 하나씩 수작업으로 처리하면 너무 느립니다. 공장에서는 컨베이어 벨트(Chunk)로 일정량씩 묶어 처리합니다. 재료를 가져오는 사람(ItemReader), 가공하는 사람(ItemProcessor), 포장해서 내보내는 사람(ItemWriter)이 분업합니다. 만약 중간에 기계가 멈춰도(실패), 처리된 부분부터 재시작할 수 있습니다.

---

## 2. Spring Batch 도메인 구조

```mermaid
graph TD
    A[JobLauncher] -->|"실행"| B[Job]
    B -->|"포함"| C[Step 1]
    B -->|"포함"| D[Step 2]
    B -->|"포함"| E[Step 3]

    C --> F["Tasklet 방식"]
    D --> G["Chunk 방식"]
    G --> H[ItemReader]
    G --> I[ItemProcessor]
    G --> J[ItemWriter]

    K[JobRepository] -->|"메타데이터 저장"| B
    K -->|"실행 이력 관리"| C

    L[JobParameters] -->|"파라미터 전달"| B
```

### 2.1 메타 테이블 구조

Spring Batch는 실행 이력을 DB에 저장합니다.

```mermaid
erDiagram
    BATCH_JOB_INSTANCE ||--o{ BATCH_JOB_EXECUTION : "has"
    BATCH_JOB_EXECUTION ||--o{ BATCH_JOB_EXECUTION_PARAMS : "has"
    BATCH_JOB_EXECUTION ||--o{ BATCH_STEP_EXECUTION : "has"
    BATCH_JOB_EXECUTION ||--|| BATCH_JOB_EXECUTION_CONTEXT : "has"
    BATCH_STEP_EXECUTION ||--|| BATCH_STEP_EXECUTION_CONTEXT : "has"

    BATCH_JOB_INSTANCE {
        BIGINT JOB_INSTANCE_ID PK
        VARCHAR JOB_NAME
        VARCHAR JOB_KEY
    }
    BATCH_JOB_EXECUTION {
        BIGINT JOB_EXECUTION_ID PK
        BIGINT JOB_INSTANCE_ID FK
        VARCHAR STATUS
        VARCHAR EXIT_CODE
        DATETIME START_TIME
        DATETIME END_TIME
    }
    BATCH_STEP_EXECUTION {
        BIGINT STEP_EXECUTION_ID PK
        BIGINT JOB_EXECUTION_ID FK
        VARCHAR STEP_NAME
        BIGINT READ_COUNT
        BIGINT WRITE_COUNT
        BIGINT SKIP_COUNT
        VARCHAR STATUS
    }
```

---

## 3. Job 설정

```java
@Configuration
@EnableBatchProcessing
public class BatchConfig {

    @Bean
    public Job importUserJob(JobRepository jobRepository,
                              Step step1, Step step2,
                              JobCompletionNotificationListener listener) {
        return new JobBuilder("importUserJob", jobRepository)
            .incrementer(new RunIdIncrementer())  // 매번 새 JobInstance 생성
            .listener(listener)
            .start(step1)
            .next(step2)
            .build();
    }
}
```

### 3.1 Job 흐름 제어

```java
@Bean
public Job conditionalJob(JobRepository jobRepository) {
    return new JobBuilder("conditionalJob", jobRepository)
        .start(step1())
            .on("COMPLETED").to(step2())  // 성공 시
            .on("FAILED").to(failureStep())  // 실패 시
        .from(step2())
            .on("*").to(step3())  // 항상
        .from(failureStep())
            .on("*").end()  // 종료
        .end()
        .build();
}
```

```mermaid
flowchart TD
    A[Step 1] -->|COMPLETED| B[Step 2]
    A -->|FAILED| C[Failure Step]
    B --> D[Step 3]
    C --> E["Job 종료"]
    D --> F["Job 완료"]
```

---

## 4. Chunk 기반 처리

### 4.1 Chunk 처리 흐름

```mermaid
sequenceDiagram
    participant S as Step
    participant R as ItemReader
    participant P as ItemProcessor
    participant W as ItemWriter
    participant TX as Transaction

    S->>TX: 트랜잭션 시작
    loop chunk-size 만큼 반복
        S->>R: read() 호출
        R-->>S: 아이템 1개
        S->>P: process(item)
        P-->>S: 처리된 아이템
    end
    S->>W: write(chunk) 한 번에 전달
    W-->>S: 완료
    S->>TX: 트랜잭션 커밋

    Note over S: null 반환될 때까지 반복
    Note over S: 다음 chunk 시작
```

### 4.2 기본 Chunk Step 구성

```java
@Bean
public Step chunkStep(JobRepository jobRepository,
                       PlatformTransactionManager transactionManager) {
    return new StepBuilder("chunkStep", jobRepository)
        .<User, ProcessedUser>chunk(100, transactionManager) // chunk size: 100
        .reader(userItemReader())
        .processor(userItemProcessor())
        .writer(userItemWriter())
        .faultTolerant()
        .skipLimit(10)
        .skip(ValidationException.class)
        .retryLimit(3)
        .retry(DeadlockLoserDataAccessException.class)
        .build();
}
```

---

## 5. ItemReader 구현

### 5.1 JdbcCursorItemReader (대용량 DB 읽기)

```java
@Bean
public JdbcCursorItemReader<User> jdbcCursorItemReader(DataSource dataSource) {
    return new JdbcCursorItemReaderBuilder<User>()
        .name("userItemReader")
        .dataSource(dataSource)
        .sql("SELECT id, name, email, status FROM users WHERE status = 'ACTIVE'")
        .rowMapper(new BeanPropertyRowMapper<>(User.class))
        .fetchSize(100)  // DB에서 한 번에 가져오는 크기
        .build();
}
```

### 5.2 JdbcPagingItemReader (페이지 단위 읽기)

```java
@Bean
public JdbcPagingItemReader<User> jdbcPagingItemReader(DataSource dataSource) {
    Map<String, Order> sortKeys = new HashMap<>();
    sortKeys.put("id", Order.ASCENDING);

    return new JdbcPagingItemReaderBuilder<User>()
        .name("pagingUserReader")
        .dataSource(dataSource)
        .selectClause("SELECT id, name, email")
        .fromClause("FROM users")
        .whereClause("WHERE status = 'ACTIVE'")
        .sortKeys(sortKeys)
        .pageSize(100)
        .rowMapper(new BeanPropertyRowMapper<>(User.class))
        .build();
}
```

### 5.3 FlatFileItemReader (CSV 읽기)

```java
@Bean
public FlatFileItemReader<UserCsvDto> csvItemReader() {
    return new FlatFileItemReaderBuilder<UserCsvDto>()
        .name("csvUserReader")
        .resource(new ClassPathResource("users.csv"))
        .delimited()
        .delimiter(",")
        .names("id", "name", "email", "age")
        .targetType(UserCsvDto.class)
        .linesToSkip(1)  // 헤더 행 스킵
        .build();
}
```

### 5.4 커스텀 ItemReader

```java
@Component
@StepScope
public class ApiItemReader implements ItemReader<ExternalData> {

    private final ExternalApiClient apiClient;
    private final List<ExternalData> buffer = new ArrayList<>();
    private int nextIndex = 0;
    private int page = 0;
    private static final int PAGE_SIZE = 100;

    @Override
    public ExternalData read() throws Exception {
        if (nextIndex >= buffer.size()) {
            fetchNextPage();
            if (buffer.isEmpty()) {
                return null; // 데이터 끝
            }
        }
        return buffer.get(nextIndex++);
    }

    private void fetchNextPage() {
        buffer.clear();
        nextIndex = 0;
        List<ExternalData> data = apiClient.fetchPage(page++, PAGE_SIZE);
        buffer.addAll(data);
    }
}
```

---

## 6. ItemProcessor 구현

```java
@Component
@StepScope
public class UserItemProcessor implements ItemProcessor<User, ProcessedUser> {

    private final EmailValidator emailValidator;

    @Override
    public ProcessedUser process(User user) throws Exception {
        // null 반환 시 해당 아이템은 건너뜀 (skip)
        if (!emailValidator.isValid(user.getEmail())) {
            log.warn("유효하지 않은 이메일, 건너뜀: {}", user.getEmail());
            return null;
        }

        if (user.getAge() < 18) {
            return null; // 미성년자 제외
        }

        // 데이터 변환
        return ProcessedUser.builder()
            .userId(user.getId())
            .fullName(user.getFirstName() + " " + user.getLastName())
            .email(user.getEmail().toLowerCase())
            .processedAt(LocalDateTime.now())
            .build();
    }
}
```

### 6.1 CompositeItemProcessor — 여러 Processor 체인

```java
@Bean
public CompositeItemProcessor<User, FinalUser> compositeProcessor() {
    CompositeItemProcessor<User, FinalUser> processor = new CompositeItemProcessor<>();
    processor.setDelegates(List.of(
        new ValidationProcessor(),
        new TransformProcessor(),
        new EnrichmentProcessor()
    ));
    return processor;
}
```

---

## 7. ItemWriter 구현

### 7.1 JdbcBatchItemWriter

```java
@Bean
public JdbcBatchItemWriter<ProcessedUser> jdbcBatchItemWriter(DataSource dataSource) {
    return new JdbcBatchItemWriterBuilder<ProcessedUser>()
        .itemSqlParameterSourceProvider(new BeanPropertyItemSqlParameterSourceProvider<>())
        .sql("INSERT INTO processed_users (user_id, full_name, email, processed_at) " +
             "VALUES (:userId, :fullName, :email, :processedAt) " +
             "ON DUPLICATE KEY UPDATE full_name = :fullName, email = :email")
        .dataSource(dataSource)
        .build();
}
```

### 7.2 FlatFileItemWriter (CSV 출력)

```java
@Bean
@StepScope
public FlatFileItemWriter<ProcessedUser> csvItemWriter(
        @Value("#{jobParameters['outputFile']}") String outputFile) {

    BeanWrapperFieldExtractor<ProcessedUser> extractor = new BeanWrapperFieldExtractor<>();
    extractor.setNames(new String[]{"userId", "fullName", "email"});

    DelimitedLineAggregator<ProcessedUser> aggregator = new DelimitedLineAggregator<>();
    aggregator.setDelimiter(",");
    aggregator.setFieldExtractor(extractor);

    return new FlatFileItemWriterBuilder<ProcessedUser>()
        .name("csvUserWriter")
        .resource(new FileSystemResource(outputFile))
        .lineAggregator(aggregator)
        .headerCallback(writer -> writer.write("userId,fullName,email"))
        .append(false)
        .build();
}
```

### 7.3 CompositeItemWriter

```java
@Bean
public CompositeItemWriter<ProcessedUser> compositeWriter() {
    CompositeItemWriter<ProcessedUser> writer = new CompositeItemWriter<>();
    writer.setDelegates(List.of(
        jdbcBatchItemWriter(),    // DB 저장
        csvItemWriter(),           // CSV 파일 출력
        kafkaItemWriter()          // Kafka 발행
    ));
    return writer;
}
```

---

## 8. Tasklet 방식

단순하거나 단일 작업에 적합합니다.

```java
// 파일 삭제 Tasklet
@Component
public class FileCleanupTasklet implements Tasklet {

    @Value("${batch.temp-dir}")
    private String tempDir;

    @Override
    public RepeatStatus execute(StepContribution contribution, ChunkContext chunkContext)
            throws Exception {
        File directory = new File(tempDir);
        if (directory.exists()) {
            FileUtils.cleanDirectory(directory);
            log.info("임시 디렉토리 정리 완료: {}", tempDir);
        }
        return RepeatStatus.FINISHED; // CONTINUABLE 반환 시 반복 실행
    }
}

// Step에 적용
@Bean
public Step cleanupStep(JobRepository jobRepository,
                         PlatformTransactionManager transactionManager) {
    return new StepBuilder("cleanupStep", jobRepository)
        .tasklet(fileCleanupTasklet(), transactionManager)
        .build();
}
```

### 8.1 Chunk vs Tasklet 비교

| 항목 | Chunk | Tasklet |
|------|-------|---------|
| 처리 단위 | N개씩 묶어 처리 | 전체를 한 번에 |
| 트랜잭션 | Chunk 단위 | Step 전체 |
| 재시작 | Chunk 단위 재시작 가능 | 처음부터 재시작 |
| 적합한 경우 | 대용량 데이터 처리 | DB 테이블 초기화, 파일 조작, API 단순 호출 |
| 메모리 | 효율적 | 단순 |

---

## 9. JobParameters와 @StepScope

```java
// JobParameters 전달
JobParameters params = new JobParametersBuilder()
    .addString("targetDate", "2026-05-02")
    .addLong("batchSize", 500L)
    .addString("outputPath", "/data/output/")
    .toJobParameters();

jobLauncher.run(importJob, params);
```

```java
// @StepScope: Step 실행 시점에 빈 생성 (JobParameters 접근 가능)
@Bean
@StepScope
public JdbcCursorItemReader<Order> orderReader(
        DataSource dataSource,
        @Value("#{jobParameters['targetDate']}") String targetDate) {

    return new JdbcCursorItemReaderBuilder<Order>()
        .name("orderReader")
        .dataSource(dataSource)
        .sql("SELECT * FROM orders WHERE order_date = ?")
        .preparedStatementSetter(ps -> ps.setString(1, targetDate))
        .rowMapper(new BeanPropertyRowMapper<>(Order.class))
        .build();
}
```

---

## 10. 파티셔닝 — 병렬 처리

### 10.1 파티셔닝 구조

```mermaid
graph TD
    A[Master Step] -->|"파티션 생성"| B[Partitioner]
    B --> C["Worker Step 1: ID 1~100000"]
    B --> D["Worker Step 2: ID 100001~200000"]
    B --> E["Worker Step 3: ID 200001~300000"]
    B --> F["Worker Step N: ..."]

    C --> G["각자 독립적으로 처리"]
    D --> G
    E --> G
    F --> G
```

```java
@Bean
public Step masterStep(JobRepository jobRepository,
                        TaskExecutor taskExecutor) {
    return new StepBuilder("masterStep", jobRepository)
        .partitioner("workerStep", rangePartitioner())
        .step(workerStep())
        .gridSize(4)  // 파티션 수
        .taskExecutor(taskExecutor)
        .build();
}

@Bean
public Partitioner rangePartitioner() {
    return gridSize -> {
        Map<String, ExecutionContext> partitions = new HashMap<>();
        long totalCount = userRepository.count();
        long partitionSize = totalCount / gridSize;

        for (int i = 0; i < gridSize; i++) {
            ExecutionContext context = new ExecutionContext();
            context.putLong("minId", i * partitionSize + 1);
            context.putLong("maxId", (i == gridSize - 1) ? totalCount : (i + 1) * partitionSize);
            partitions.put("partition" + i, context);
        }
        return partitions;
    };
}

@Bean
@StepScope
public JdbcCursorItemReader<User> partitionedReader(
        DataSource dataSource,
        @Value("#{stepExecutionContext['minId']}") Long minId,
        @Value("#{stepExecutionContext['maxId']}") Long maxId) {

    return new JdbcCursorItemReaderBuilder<User>()
        .name("partitionedUserReader")
        .dataSource(dataSource)
        .sql("SELECT * FROM users WHERE id BETWEEN ? AND ?")
        .preparedStatementSetter(ps -> {
            ps.setLong(1, minId);
            ps.setLong(2, maxId);
        })
        .rowMapper(new BeanPropertyRowMapper<>(User.class))
        .build();
}
```

### 10.2 멀티스레드 Step

```java
@Bean
public TaskExecutor batchTaskExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(4);
    executor.setMaxPoolSize(8);
    executor.setQueueCapacity(100);
    executor.setThreadNamePrefix("batch-");
    executor.initialize();
    return executor;
}

@Bean
public Step multiThreadStep(JobRepository jobRepository,
                             PlatformTransactionManager transactionManager) {
    return new StepBuilder("multiThreadStep", jobRepository)
        .<User, ProcessedUser>chunk(100, transactionManager)
        .reader(synchronizedReader())  // 스레드 안전한 Reader 필요!
        .processor(userProcessor())
        .writer(userWriter())
        .taskExecutor(batchTaskExecutor())
        .throttleLimit(4)
        .build();
}

// JdbcPagingItemReader는 Thread-safe, CursorItemReader는 동기화 필요
@Bean
public SynchronizedItemStreamReader<User> synchronizedReader() {
    return new SynchronizedItemStreamReaderBuilder<User>()
        .delegate(jdbcCursorItemReader())
        .build();
}
```

---

## 11. 재시작과 재시도

### 11.1 재시작 (Restart)

```java
// 실패한 Job 재시작 — JobRepository가 이전 상태를 기억
jobLauncher.run(job, lastFailedJobParams); // 실패한 Step부터 재시작

// 특정 Step을 항상 처음부터 실행하도록 설정
@Bean
public Step alwaysRestartStep(JobRepository jobRepository) {
    return new StepBuilder("alwaysRestartStep", jobRepository)
        .<User, ProcessedUser>chunk(100, transactionManager)
        .allowStartIfComplete(true)  // 완료돼도 재실행 허용
        .startLimit(3)  // 최대 3번까지만 시작 허용
        .reader(reader())
        .writer(writer())
        .build();
}
```

### 11.2 Skip (건너뛰기)

```java
@Bean
public Step skipableStep(JobRepository jobRepository) {
    return new StepBuilder("skipableStep", jobRepository)
        .<User, ProcessedUser>chunk(100, transactionManager)
        .reader(reader())
        .processor(processor())
        .writer(writer())
        .faultTolerant()
        .skipLimit(5)  // 최대 5건까지 skip 허용
        .skip(ValidationException.class)
        .skip(ParseException.class)
        .noSkip(DatabaseException.class)  // 이 예외는 skip 금지
        .skipPolicy(new AlwaysSkipItemSkipPolicy())
        .listener(new SkipListener<User, ProcessedUser>() {
            @Override
            public void onSkipInRead(Throwable t) {
                log.warn("읽기 중 skip: {}", t.getMessage());
            }
            @Override
            public void onSkipInProcess(User item, Throwable t) {
                log.warn("처리 중 skip, item={}: {}", item.getId(), t.getMessage());
            }
            @Override
            public void onSkipInWrite(ProcessedUser item, Throwable t) {
                log.warn("쓰기 중 skip, item={}: {}", item.getUserId(), t.getMessage());
            }
        })
        .build();
}
```

---

## 12. 스케줄링 연동

### 12.1 Spring Scheduler + Batch

```java
@Component
@EnableScheduling
public class BatchScheduler {

    private final JobLauncher jobLauncher;
    private final Job dailyReportJob;

    // 매일 새벽 2시 실행
    @Scheduled(cron = "0 0 2 * * ?")
    public void runDailyReport() {
        try {
            JobParameters params = new JobParametersBuilder()
                .addString("date", LocalDate.now().toString())
                .addLong("time", System.currentTimeMillis())
                .toJobParameters();

            JobExecution execution = jobLauncher.run(dailyReportJob, params);
            log.info("배치 실행 상태: {}", execution.getStatus());
        } catch (Exception e) {
            log.error("배치 실행 실패", e);
        }
    }
}
```

### 12.2 JobLauncher 비동기 설정

```java
@Bean
public JobLauncher asyncJobLauncher(JobRepository jobRepository) throws Exception {
    TaskExecutorJobLauncher jobLauncher = new TaskExecutorJobLauncher();
    jobLauncher.setJobRepository(jobRepository);
    jobLauncher.setTaskExecutor(new SimpleAsyncTaskExecutor()); // 비동기 실행
    jobLauncher.afterPropertiesSet();
    return jobLauncher;
}
```

---

## 13. 극한 시나리오 — 1억 건 처리

```java
@Configuration
public class LargeScaleBatchConfig {

    // 1. JPA 대신 JDBC 사용 (성능)
    // 2. Cursor 대신 Paging (메모리)
    // 3. 파티셔닝 (병렬)
    // 4. 청크 사이즈 튜닝

    @Bean
    public Job processHundredMillionRecords(JobRepository jobRepository) {
        return new JobBuilder("hundredMillionJob", jobRepository)
            .start(masterStep())
            .build();
    }

    @Bean
    public Step masterStep() {
        return new StepBuilder("masterStep", jobRepository)
            .partitioner("workerStep", columnRangePartitioner())
            .step(workerStep())
            .gridSize(10)  // 10개 파티션
            .taskExecutor(partitionTaskExecutor())
            .build();
    }

    @Bean
    @StepScope
    public JdbcPagingItemReader<RawData> largeReader(
            @Value("#{stepExecutionContext['minId']}") Long minId,
            @Value("#{stepExecutionContext['maxId']}") Long maxId) {

        return new JdbcPagingItemReaderBuilder<RawData>()
            .name("largeReader")
            .dataSource(dataSource)
            .selectClause("SELECT id, data")
            .fromClause("FROM raw_data")
            .whereClause("WHERE id BETWEEN " + minId + " AND " + maxId)
            .sortKeys(Map.of("id", Order.ASCENDING))
            .pageSize(1000)  // 청크 사이즈와 일치 권장
            .rowMapper(new BeanPropertyRowMapper<>(RawData.class))
            .build();
    }

    @Bean
    public Step workerStep() {
        return new StepBuilder("workerStep", jobRepository)
            .<RawData, ProcessedData>chunk(1000, transactionManager) // 1000건씩
            .reader(largeReader(null, null))
            .processor(rawDataProcessor())
            .writer(processedDataWriter())
            .faultTolerant()
            .skipLimit(1000)
            .skip(Exception.class)
            .build();
    }
}
```

예상 처리 시간 (10개 파티션, 청크 1000):
- 단순 처리: 1억 / 10 / 1000 = 10,000회 쓰기 작업
- DB 쓰기 지연 10ms 기준: 100초 수준

---

## 14. 전체 흐름 정리

```mermaid
flowchart TD
    A[JobLauncher.run] --> B["JobRepository에 JobExecution 생성"]
    B --> C["Job 실행"]
    C --> D["Step 1 시작"]
    D --> E{"Chunk 기반?"}
    E -->|Yes| F[ItemReader.read × chunkSize]
    F --> G[ItemProcessor.process × chunkSize]
    G --> H[ItemWriter.write chunk]
    H --> I["트랜잭션 커밋"]
    I --> J{"더 읽을 데이터?"}
    J -->|Yes| F
    J -->|No| K["Step 완료"]
    E -->|No| L[Tasklet.execute]
    L --> K
    K --> M{"다음 Step?"}
    M -->|Yes| D
    M -->|No| N["Job 완료"]
    N --> O["JobRepository에 상태 저장"]
```

---

## 15. 요약

| 개념 | 설명 | 핵심 포인트 |
|------|------|-----------|
| Job | 배치 작업 단위 | 여러 Step으로 구성 |
| Step | Job의 처리 단계 | Chunk or Tasklet |
| Chunk | N건씩 묶어 처리 | Read → Process → Write |
| ItemReader | 데이터 읽기 | null 반환 시 종료 |
| ItemProcessor | 데이터 변환/필터 | null 반환 시 해당 건 skip |
| ItemWriter | 데이터 저장 | 리스트 단위로 받음 |
| Tasklet | 단순 작업 | FINISHED or CONTINUABLE |
| @StepScope | Step 실행 시 빈 생성 | JobParameters 주입 가능 |
| 파티셔닝 | 데이터를 나눠 병렬 처리 | 대용량 필수 기법 |
| JobRepository | 배치 메타데이터 관리 | 재시작 핵심 |
