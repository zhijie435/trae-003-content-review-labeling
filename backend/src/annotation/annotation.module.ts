import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AnnotationService } from './annotation.service';
import { AnnotationController } from './annotation.controller';
import { Annotation } from './annotation.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Annotation])],
  controllers: [AnnotationController],
  providers: [AnnotationService],
})
export class AnnotationModule {}
