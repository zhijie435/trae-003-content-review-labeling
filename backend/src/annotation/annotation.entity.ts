import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn } from 'typeorm';

export enum AnnotationType {
  TEXT = 'text',
  IMAGE = 'image',
}

export enum AnnotationStatus {
  PENDING = 'pending',
  ANNOTATED = 'annotated',
  REVIEWED = 'reviewed',
}

export enum AnnotationResult {
  PASS = 'pass',
  VIOLATION = 'violation',
  SUSPICIOUS = 'suspicious',
}

@Entity()
export class Annotation {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({
    type: 'simple-enum',
    enum: AnnotationType,
  })
  type: AnnotationType;

  @Column('text', { nullable: true })
  content: string;

  @Column({ nullable: true })
  imageUrl: string;

  @Column({
    type: 'simple-enum',
    enum: AnnotationResult,
    nullable: true,
  })
  result: AnnotationResult;

  @Column('text', { nullable: true })
  tags: string;

  @Column('text', { nullable: true })
  remark: string;

  @Column({
    type: 'simple-enum',
    enum: AnnotationStatus,
    default: AnnotationStatus.PENDING,
  })
  status: AnnotationStatus;

  @Column({ nullable: true })
  annotator: string;

  @Column({ nullable: true })
  reviewer: string;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;
}
