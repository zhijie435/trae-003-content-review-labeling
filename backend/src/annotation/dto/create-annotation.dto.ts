import { IsEnum, IsOptional, IsString, IsUrl } from 'class-validator';
import { AnnotationType, AnnotationResult } from '../annotation.entity';

export class CreateTextAnnotationDto {
  @IsEnum(AnnotationType)
  type: AnnotationType.TEXT;

  @IsString()
  content: string;

  @IsOptional()
  @IsEnum(AnnotationResult)
  result?: AnnotationResult;

  @IsOptional()
  @IsString()
  tags?: string;

  @IsOptional()
  @IsString()
  remark?: string;

  @IsOptional()
  @IsString()
  annotator?: string;
}

export class CreateImageAnnotationDto {
  @IsEnum(AnnotationType)
  type: AnnotationType.IMAGE;

  @IsUrl()
  imageUrl: string;

  @IsOptional()
  @IsString()
  content?: string;

  @IsOptional()
  @IsEnum(AnnotationResult)
  result?: AnnotationResult;

  @IsOptional()
  @IsString()
  tags?: string;

  @IsOptional()
  @IsString()
  remark?: string;

  @IsOptional()
  @IsString()
  annotator?: string;
}

export type CreateAnnotationDto = CreateTextAnnotationDto | CreateImageAnnotationDto;

export class UpdateAnnotationDto {
  @IsOptional()
  @IsEnum(AnnotationResult)
  result?: AnnotationResult;

  @IsOptional()
  @IsString()
  tags?: string;

  @IsOptional()
  @IsString()
  remark?: string;

  @IsOptional()
  @IsString()
  annotator?: string;

  @IsOptional()
  @IsString()
  reviewer?: string;
}
